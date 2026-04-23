from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent.mmwiki.core import Context, MMWikiService
from agent.mmwiki.errors import DriftError


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


if __name__ == "__main__":
    unittest.main()

