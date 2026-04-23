from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent.mmwiki.core import Context, MMWikiService
from agent.mmwiki.errors import DriftError
from agent.mmwiki.index import IndexedDoc
from agent.mmwiki.state import get_snapshot


class _Response:
    def __init__(self, text: str, parsed=None, json=None):
        self.text = text
        self.parsed = parsed
        self.json = json


class _Client:
    def __init__(self) -> None:
        self.modify_calls = 0

    def get(self, path: str):
        if path.startswith("/page/view"):
            return _Response(
                '<h3 class="view-page-title">Doc</h3><div id="document_page_view"><textarea>old</textarea></div>'
            )
        raise ValueError(path)

    def post(self, path: str, data):
        if path == "/page/modify":
            self.modify_calls += 1
            return _Response("", parsed={"ok": True, "redirect": {"url": ""}})
        return _Response("", parsed={"ok": True, "redirect": {"url": "/document/index?document_id=1"}})

    def upload_file(self, path, *, field, file_path, extra_fields=None):
        raise AssertionError("no asset upload expected")


class _AnalyzeClient:
    def __init__(self) -> None:
        self.docs = {
            "2": {
                "name": "Remote Doc",
                "content": "Remote systems run backups daily. Backup status is tracked for ops teams.",
            }
        }
        self.fetch_count = 0

    def get(self, path: str):
        if path.startswith("/page/view"):
            self.fetch_count += 1
            doc_id = path.split("document_id=", 1)[1]
            doc = self.docs[doc_id]
            return _Response(
                f'<h3 class="view-page-title">{doc["name"]}</h3>'
                f'<div id="document_page_view"><textarea>{doc["content"]}</textarea></div>'
            )
        raise ValueError(path)

    def post(self, path: str, data):
        return _Response("", parsed={"ok": True, "redirect": {"url": ""}})

    def upload_file(self, path, *, field, file_path, extra_fields=None):
        raise AssertionError("no asset upload expected")


class CoreDriftTests(unittest.TestCase):
    def test_push_blocks_when_drifted(self) -> None:
        with TemporaryDirectory() as tmpdir:
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmpdir) / "cfg")
            os.environ["XDG_DATA_HOME"] = str(Path(tmpdir) / "data")
            md = Path(tmpdir) / "doc.md"
            md.write_text("new", encoding="utf-8")
            client = _Client()
            ctx = Context(client=client, server="http://x", profile="p", output_json=True)
            service = MMWikiService(ctx)
            from agent.mmwiki.state import set_snapshot

            set_snapshot("http://x", "p", "1", str(md), "different", "Doc")
            with self.assertRaises(DriftError):
                service.doc_push(document_id="1", md_path=str(md), force=False, comment="test")
            self.assertEqual(client.modify_calls, 0)

    def test_doc_delete_local_cleans_snapshot_and_retains_index(self) -> None:
        with TemporaryDirectory() as tmpdir:
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmpdir) / "cfg")
            os.environ["XDG_DATA_HOME"] = str(Path(tmpdir) / "data")
            md = Path(tmpdir) / "doc.md"
            md.write_text("hello", encoding="utf-8")
            client = _Client()
            ctx = Context(client=client, server="http://x", profile="p", output_json=True)
            service = MMWikiService(ctx)
            from agent.mmwiki.state import set_snapshot

            set_snapshot("http://x", "p", "1", str(md), "abc", "Doc")
            service.index.upsert(
                server="http://x",
                profile="p",
                doc=IndexedDoc(document_id="1", title="Doc", content="hello", md_path=str(md)),
            )

            result = service.doc_delete_local(md_path=str(md), document_id="1")
            self.assertTrue(result["removed_file"])
            self.assertTrue(result["retained_index"])
            self.assertEqual(result["removed_index"], 0)
            self.assertFalse(md.exists())
            self.assertIsNone(get_snapshot("http://x", "p", "1", str(md)))
            docs = service.index.get_documents_by_ids(
                server="http://x",
                profile="p",
                document_ids=["1"],
            )
            self.assertIn("1", docs)

    def test_analyze_summary_and_keywords_with_remote_fetch(self) -> None:
        with TemporaryDirectory() as tmpdir:
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmpdir) / "cfg")
            os.environ["XDG_DATA_HOME"] = str(Path(tmpdir) / "data")
            client = _AnalyzeClient()
            service = MMWikiService(
                Context(client=client, server="http://x", profile="p", output_json=True)
            )
            service.index.upsert(
                server="http://x",
                profile="p",
                doc=IndexedDoc(
                    document_id="1",
                    title="Python Guide",
                    content="Python tools improve reliability. Guide covers testing and packaging.",
                    md_path="/tmp/a.md",
                ),
            )

            summaries = service.analyze_summary(document_ids=["1", "2"], max_sentences=1)
            self.assertEqual([item["document_id"] for item in summaries], ["1", "2"])
            self.assertTrue(summaries[0]["summary"])
            self.assertTrue(summaries[1]["summary"])
            self.assertEqual(client.fetch_count, 1)

            keywords = service.analyze_keywords(document_ids=["2"], top_k=5)
            self.assertEqual(len(keywords), 1)
            self.assertLessEqual(len(keywords[0]["keywords"]), 5)
            self.assertTrue(any(token.startswith("backup") for token in keywords[0]["keywords"]))


if __name__ == "__main__":
    unittest.main()
