from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

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

    def search(self, *, server: str, profile: str, keyword: str, limit: int = 20) -> list[dict[str, str]]:
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
            (server, profile, keyword, limit),
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

