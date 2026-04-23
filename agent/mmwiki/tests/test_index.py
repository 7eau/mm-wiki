from __future__ import annotations

import os
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


if __name__ == "__main__":
    unittest.main()
