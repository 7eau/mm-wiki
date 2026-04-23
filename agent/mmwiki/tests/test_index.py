from __future__ import annotations

import os
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent.mmwiki.index import ContentIndex, IndexedDoc


class IndexTests(unittest.TestCase):
    def test_search_fts_prefix_and_like_fallback(self) -> None:
        with TemporaryDirectory() as tmpdir:
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmpdir) / "cfg")
            os.environ["XDG_DATA_HOME"] = str(Path(tmpdir) / "data")
            index = ContentIndex()
            index.upsert(
                server="http://x",
                profile="p",
                doc=IndexedDoc(
                    document_id="1",
                    title="Alpha Guide",
                    content="quick start document",
                    md_path="a.md",
                ),
            )

            fts_rows = index.search(server="http://x", profile="p", keyword="qui sta")
            self.assertTrue(any(item["document_id"] == "1" for item in fts_rows))

            like_rows = index.search(server="http://x", profile="p", keyword="uid")
            self.assertTrue(any(item["document_id"] == "1" for item in like_rows))

    def test_get_and_delete_documents(self) -> None:
        with TemporaryDirectory() as tmpdir:
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmpdir) / "cfg")
            os.environ["XDG_DATA_HOME"] = str(Path(tmpdir) / "data")
            index = ContentIndex()
            index.upsert(
                server="http://x",
                profile="p",
                doc=IndexedDoc(document_id="1", title="One", content="c1", md_path="a.md"),
            )
            index.upsert(
                server="http://x",
                profile="p",
                doc=IndexedDoc(document_id="2", title="Two", content="c2", md_path="b.md"),
            )

            docs = index.get_documents_by_ids(server="http://x", profile="p", document_ids=["1", "2"])
            self.assertEqual(set(docs.keys()), {"1", "2"})

            removed = index.delete_documents(server="http://x", profile="p", md_path="a.md")
            self.assertEqual(removed, 1)
            docs_after = index.get_documents_by_ids(server="http://x", profile="p", document_ids=["1", "2"])
            self.assertEqual(set(docs_after.keys()), {"2"})

    def test_export_and_install_database(self) -> None:
        with TemporaryDirectory() as tmpdir:
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmpdir) / "cfg")
            os.environ["XDG_DATA_HOME"] = str(Path(tmpdir) / "data")
            index = ContentIndex()
            index.upsert(
                server="http://x",
                profile="p",
                doc=IndexedDoc(document_id="1", title="One", content="c1", md_path="a.md"),
            )
            export_path = Path(tmpdir) / "portable.db"
            export_result = index.export_database(out_path=str(export_path))
            self.assertTrue(export_result["exported"])
            self.assertEqual(export_result["document_count"], 1)
            self.assertTrue(export_path.exists())
            with sqlite3.connect(export_path) as conn:
                row = conn.execute("SELECT COUNT(1) FROM documents").fetchone()
            self.assertEqual(int(row[0]), 1)

            with TemporaryDirectory() as tmpdir2:
                os.environ["XDG_CONFIG_HOME"] = str(Path(tmpdir2) / "cfg")
                os.environ["XDG_DATA_HOME"] = str(Path(tmpdir2) / "data")
                other_index = ContentIndex()
                other_index.upsert(
                    server="http://x",
                    profile="p",
                    doc=IndexedDoc(document_id="9", title="Old", content="legacy", md_path="old.md"),
                )
                install_result = other_index.install_database(from_path=str(export_path))
                self.assertTrue(install_result["installed"])
                self.assertIsNotNone(install_result["backup_path"])
                self.assertEqual(install_result["document_count"], 1)
                docs = other_index.get_documents_by_ids(
                    server="http://x",
                    profile="p",
                    document_ids=["1", "9"],
                )
                self.assertIn("1", docs)
                self.assertNotIn("9", docs)

    def test_install_database_rejects_invalid_source(self) -> None:
        with TemporaryDirectory() as tmpdir:
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmpdir) / "cfg")
            os.environ["XDG_DATA_HOME"] = str(Path(tmpdir) / "data")
            index = ContentIndex()
            invalid = Path(tmpdir) / "bad.db"
            invalid.write_text("not-a-sqlite", encoding="utf-8")
            with self.assertRaises(ValueError):
                index.install_database(from_path=str(invalid))


if __name__ == "__main__":
    unittest.main()
