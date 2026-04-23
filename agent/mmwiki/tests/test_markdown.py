from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent.mmwiki.markdown import rewrite_markdown_assets


class _FakeResponse:
    def __init__(self, *, parsed=None, json=None, text="") -> None:
        self.parsed = parsed
        self.json = json
        self.text = text


class _FakeClient:
    def __init__(self) -> None:
        self.upload_calls = []
        self.get_calls = []

    def upload_file(self, path: str, *, field: str, file_path: str, extra_fields=None):
        self.upload_calls.append((path, field, file_path))
        if field == "editormd-image-file":
            return _FakeResponse(json={"success": 1, "url": "/images/1/2/a.png"})
        return _FakeResponse(parsed={"ok": True})

    def get(self, path: str):
        self.get_calls.append(path)
        return _FakeResponse(
            text='<td>doc.pdf</td><td><a href="/attachment/download?attachment_id=9">下载</a></td>'
        )


class MarkdownRewriteTests(unittest.TestCase):
    def test_rewrite_assets(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "a.png").write_bytes(b"img")
            (root / "doc.pdf").write_bytes(b"pdf")
            client = _FakeClient()
            original = "![img](a.png)\n[att](doc.pdf)\n[ext](https://example.com)"
            output = rewrite_markdown_assets(client, "2", original, str(root / "doc.md"))
            self.assertIn("![img](/images/1/2/a.png)", output)
            self.assertIn("[att](/attachment/download?attachment_id=9)", output)
            self.assertIn("[ext](https://example.com)", output)


if __name__ == "__main__":
    unittest.main()

