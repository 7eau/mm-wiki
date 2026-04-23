from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
import shutil
from uuid import uuid4

from .paths import data_dir, ensure_dirs


@dataclass
class IndexedDoc:
    document_id: str
    title: str
    content: str
    md_path: str


def _db_path() -> Path:
    ensure_dirs()
    return data_dir() / "index" / "content.db"


class ContentIndex:
    def __init__(self) -> None:
        self.conn = sqlite3.connect(_db_path())
        self._init_schema()

    @staticmethod
    def db_path() -> Path:
        return _db_path()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT NOT NULL,
                server TEXT NOT NULL,
                profile TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                md_path TEXT NOT NULL,
                PRIMARY KEY (document_id, server, profile)
            )
            """
        )
        self.conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                document_id UNINDEXED,
                server UNINDEXED,
                profile UNINDEXED,
                title,
                content
            )
            """
        )
        self.conn.commit()

    def upsert(self, *, server: str, profile: str, doc: IndexedDoc) -> None:
        self.conn.execute(
            """
            INSERT INTO documents(document_id, server, profile, title, content, md_path)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(document_id, server, profile)
            DO UPDATE SET title=excluded.title, content=excluded.content, md_path=excluded.md_path
            """,
            (doc.document_id, server, profile, doc.title, doc.content, doc.md_path),
        )
        self.conn.execute(
            "DELETE FROM documents_fts WHERE document_id=? AND server=? AND profile=?",
            (doc.document_id, server, profile),
        )
        self.conn.execute(
            """
            INSERT INTO documents_fts(document_id, server, profile, title, content)
            VALUES (?, ?, ?, ?, ?)
            """,
            (doc.document_id, server, profile, doc.title, doc.content),
        )
        self.conn.commit()

    def document_count(self) -> int:
        row = self.conn.execute("SELECT COUNT(1) FROM documents").fetchone()
        return int(row[0]) if row else 0

    def search(self, *, server: str, profile: str, keyword: str, limit: int = 20) -> list[dict[str, str]]:
        rows: list[tuple] = []
        fts_keyword = self._build_fts_keyword(keyword)
        if fts_keyword:
            try:
                rows = self.conn.execute(
                    """
                    SELECT f.document_id, d.title, d.md_path,
                           snippet(documents_fts, 4, '[', ']', '…', 18) AS snippet
                    FROM documents_fts f
                    JOIN documents d
                    ON d.document_id=f.document_id AND d.server=f.server AND d.profile=f.profile
                    WHERE f.server=? AND f.profile=? AND documents_fts MATCH ?
                    LIMIT ?
                    """,
                    (server, profile, fts_keyword, limit),
                ).fetchall()
            except sqlite3.OperationalError:
                rows = []
        if not rows:
            like_keyword = f"%{keyword}%"
            rows = self.conn.execute(
                """
                SELECT document_id, title, md_path, substr(content, 1, 200)
                FROM documents
                WHERE server=? AND profile=?
                  AND (title LIKE ? OR content LIKE ?)
                LIMIT ?
                """,
                (server, profile, like_keyword, like_keyword, limit),
            ).fetchall()
        return [
            {
                "document_id": row[0],
                "title": row[1],
                "md_path": row[2],
                "snippet": row[3],
            }
            for row in rows
        ]

    def get_documents_by_ids(
        self,
        *,
        server: str,
        profile: str,
        document_ids: list[str],
    ) -> dict[str, IndexedDoc]:
        if not document_ids:
            return {}
        placeholders = ",".join("?" for _ in document_ids)
        rows = self.conn.execute(
            f"""
            SELECT document_id, title, content, md_path
            FROM documents
            WHERE server=? AND profile=? AND document_id IN ({placeholders})
            """,
            [server, profile, *document_ids],
        ).fetchall()
        return {
            row[0]: IndexedDoc(document_id=row[0], title=row[1], content=row[2], md_path=row[3])
            for row in rows
        }

    def delete_documents(
        self,
        *,
        server: str,
        profile: str,
        md_path: str | None = None,
        document_id: str | None = None,
    ) -> int:
        where = ["server=?", "profile=?"]
        params: list[str] = [server, profile]
        if md_path is not None:
            where.append("md_path=?")
            params.append(md_path)
        if document_id is not None:
            where.append("document_id=?")
            params.append(document_id)
        rows = self.conn.execute(
            f"SELECT document_id, server, profile FROM documents WHERE {' AND '.join(where)}",
            params,
        ).fetchall()
        if not rows:
            return 0
        self.conn.execute(f"DELETE FROM documents WHERE {' AND '.join(where)}", params)
        for row in rows:
            self.conn.execute(
                "DELETE FROM documents_fts WHERE document_id=? AND server=? AND profile=?",
                (row[0], row[1], row[2]),
            )
        self.conn.commit()
        return len(rows)

    def export_database(self, *, out_path: str) -> dict[str, str | int | bool]:
        target = Path(out_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.conn.commit()
        source = self.db_path().resolve()
        shutil.copy2(source, target)
        return {
            "source": str(source),
            "target": str(target),
            "document_count": self.document_count(),
            "exported": True,
        }

    def install_database(
        self,
        *,
        from_path: str,
        backup_path: str | None = None,
    ) -> dict[str, str | int | bool | None]:
        source = Path(from_path).expanduser().resolve()
        target = self.db_path().resolve()
        if source == target:
            raise ValueError("source db cannot be the active local index db")
        source_document_count = self._validate_portable_db(source)

        self.conn.commit()
        backup: Path | None = None
        if target.exists():
            backup = (
                Path(backup_path).expanduser()
                if backup_path
                else target.with_name(f"{target.stem}.backup-{datetime.now().strftime('%Y%m%d%H%M%S')}.db")
            )
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup)

        target.parent.mkdir(parents=True, exist_ok=True)
        temp_target = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
        shutil.copy2(source, temp_target)
        try:
            self.conn.close()
            os.replace(temp_target, target)
        except Exception:
            if temp_target.exists():
                temp_target.unlink()
            self.conn = sqlite3.connect(target)
            self._init_schema()
            raise

        self.conn = sqlite3.connect(target)
        self._init_schema()
        return {
            "source": str(source),
            "target": str(target),
            "backup_path": str(backup) if backup else None,
            "document_count": source_document_count,
            "installed": True,
        }

    def _build_fts_keyword(self, keyword: str) -> str:
        terms = re.findall(r"[\w\u4e00-\u9fff]+", keyword, flags=re.UNICODE)
        tokens = []
        for term in terms:
            value = term.strip()
            if not value:
                continue
            escaped = value.replace('"', '""')
            tokens.append(f'"{escaped}"*')
        return " AND ".join(tokens)

    def _validate_portable_db(self, path: Path) -> int:
        if not path.exists() or not path.is_file():
            raise ValueError(f"source db not found: {path}")
        conn = sqlite3.connect(path)
        try:
            has_documents = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='documents' LIMIT 1"
            ).fetchone()
            has_fts = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='documents_fts' LIMIT 1"
            ).fetchone()
            if not has_documents or not has_fts:
                raise ValueError("invalid index db: required tables missing")
            row = conn.execute("SELECT COUNT(1) FROM documents").fetchone()
            return int(row[0]) if row else 0
        except sqlite3.DatabaseError as exc:
            raise ValueError(f"invalid sqlite db: {path}") from exc
        finally:
            conn.close()
