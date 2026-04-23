from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent.mmwiki.core import Context, MMWikiService
from agent.mmwiki.errors import DriftError
from agent.mmwiki.index import IndexedDoc
from agent.mmwiki.markdown import sha256_text
from agent.mmwiki.state import get_snapshot


class _Response:
    def __init__(self, text: str, parsed=None, json=None, url: str = ""):
        self.text = text
        self.parsed = parsed
        self.json = json
        self.url = url


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


class _PreindexClient:
    def __init__(self) -> None:
        self.page_docs = {
            "1": ("Doc-1", "content-1"),
            "2": ("Doc-2", "content-2"),
            "4": ("Doc-4", "content-4"),
            "5": ("Doc-5", "content-5"),
            "6": ("Doc-6", "content-6"),
        }

    def get(self, path: str):
        if path.startswith("/space/document"):
            if "space_id=9" in path:
                return _Response("", parsed={}, json=None)
            return _Response("", parsed={}, json=None)
        if path.startswith("/document/index"):
            if "document_id=6" in path:
                return _Response(
                    '<script>var tree=[{"document_id":6},{"document_id":"2"},'
                    '{"document_id":6}, {"document_id":5}]</script>'
                )
            raise ValueError(path)
        if path.startswith("/page/view"):
            doc_id = path.split("document_id=", 1)[1]
            if doc_id == "3":
                from agent.mmwiki.errors import ApiError

                raise ApiError("您没有权限访问该页面！")
            if doc_id == "8":
                raise RuntimeError("unexpected crash")
            title, content = self.page_docs[doc_id]
            return _Response(
                f'<h3 class="view-page-title">{title}</h3>'
                f'<div id="document_page_view"><textarea>{content}</textarea></div>'
            )
        raise ValueError(path)

    def post(self, path: str, data):
        raise AssertionError("no post expected")

    def upload_file(self, path, *, field, file_path, extra_fields=None):
        raise AssertionError("no asset upload expected")


class _SpaceClient:
    def __init__(self) -> None:
        self.space_pages = {
            1: [
                {"space_id": "10", "name": "研发空间"},
                {"space_id": "11", "name": "产品空间"},
            ],
            2: [{"space_id": "12", "name": "失效空间"}],
            3: [],
        }
        self.space_roots = {
            "10": "1000",
            "11": "1100",
            "12": None,
            "20": "2000",
        }

    def get(self, path: str):
        if path.startswith("/space/list?page="):
            page = int(path.split("=", 1)[1])
            spaces = self.space_pages.get(page, [])
            rows = "".join(
                f'<a href="/space/document?space_id={item["space_id"]}"><strong>{item["name"]}</strong></a>'
                for item in spaces
            )
            return _Response(rows)
        if path.startswith("/space/document?space_id="):
            space_id = path.split("=", 1)[1]
            root = self.space_roots.get(space_id)
            if root:
                return _Response(
                    "",
                    parsed={},
                    json=None,
                    url=f"http://x/document/index?document_id={root}",
                )
            return _Response("", parsed={}, json=None, url=f"http://x/space/document?space_id={space_id}")
        if path.startswith("/document/index?document_id=1000"):
            return _Response(
                """
                <a href="/document/index?document_id=1000">研发首页</a>
                <script>var tree=[{"document_id":"1001","title":"平台规范"},{"document_id":"1002"}]</script>
                """
            )
        if path.startswith("/document/index?document_id=2000"):
            return _Response('<a href="/document/index?document_id=2999">孤立节点</a>')
        raise ValueError(path)

    def post(self, path: str, data):
        raise AssertionError("no post expected")

    def upload_file(self, path, *, field, file_path, extra_fields=None):
        raise AssertionError("no asset upload expected")


class _PullClient:
    def get(self, path: str):
        if path.startswith("/page/view"):
            return _Response(
                '<h3 class="view-page-title">Pulled Doc</h3>'
                '<div id="document_page_view"><textarea>'
                '![img](./img/a.png)\n[doc](../docs/b.md)\n[ext](https://example.com/c)'
                "</textarea></div>"
            )
        raise ValueError(path)

    def post(self, path: str, data):
        raise AssertionError("no post expected")

    def upload_file(self, path, *, field, file_path, extra_fields=None):
        raise AssertionError("no upload expected")


class CoreDriftTests(unittest.TestCase):
    def test_doc_pull_rewrites_markdown_and_snapshot_hash(self) -> None:
        with TemporaryDirectory() as tmpdir:
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmpdir) / "cfg")
            os.environ["XDG_DATA_HOME"] = str(Path(tmpdir) / "data")
            md = Path(tmpdir) / "pulled.md"
            client = _PullClient()
            ctx = Context(client=client, server="http://x/", profile="p", output_json=True)
            service = MMWikiService(ctx)

            result = service.doc_pull(document_id="7", md_path=str(md))

            expected_content = (
                "![img](http://x/img/a.png)\n[doc](http://x/docs/b.md)\n[ext](https://example.com/c)"
            )
            self.assertEqual(md.read_text(encoding="utf-8"), expected_content)
            expected_digest = sha256_text(expected_content)
            self.assertEqual(result["document_id"], "7")
            self.assertEqual(result["md_path"], str(md))
            self.assertEqual(result["title"], "Pulled Doc")
            self.assertEqual(result["sha256"], expected_digest)

            snapshot = get_snapshot("http://x/", "p", "7", str(md))
            self.assertIsNotNone(snapshot)
            self.assertEqual(snapshot["sha256"], expected_digest)

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

    def test_resolve_preindex_document_ids_from_union_sources(self) -> None:
        with TemporaryDirectory() as tmpdir:
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmpdir) / "cfg")
            os.environ["XDG_DATA_HOME"] = str(Path(tmpdir) / "data")
            client = _PreindexClient()
            service = MMWikiService(
                Context(client=client, server="http://x", profile="p", output_json=True)
            )

            class _SpaceResp:
                def __init__(self, url: str, text: str = "") -> None:
                    self.url = url
                    self.text = text
                    self.parsed = None
                    self.json = None

            def get_with_space(path: str):
                if path.startswith("/space/document?space_id=7"):
                    return _SpaceResp("http://x/document/index?document_id=6")
                if path.startswith("/space/document?space_id=9"):
                    return _SpaceResp("http://x/space/document?space_id=9")
                return original_get(path)

            original_get = client.get
            service.ctx.client.get = get_with_space  # type: ignore[method-assign]

            resolved = service.resolve_preindex_document_ids(
                document_ids=["1", "2", "2"],
                space_ids=["7", "9"],
                doc_range_start=4,
                doc_range_end=5,
            )
            self.assertEqual(resolved["requested_count"], 7)
            self.assertEqual(resolved["resolved_document_ids"], ["1", "2", "4", "5", "6"])
            self.assertTrue(any("space_id=9" in item for item in resolved["errors"]))

    def test_resolve_preindex_range_validation(self) -> None:
        with TemporaryDirectory() as tmpdir:
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmpdir) / "cfg")
            os.environ["XDG_DATA_HOME"] = str(Path(tmpdir) / "data")
            client = _PreindexClient()
            service = MMWikiService(
                Context(client=client, server="http://x", profile="p", output_json=True)
            )
            with self.assertRaises(ValueError):
                service.resolve_preindex_document_ids(doc_range_start=9, doc_range_end=8)

    def test_preindex_documents_continue_on_error(self) -> None:
        with TemporaryDirectory() as tmpdir:
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmpdir) / "cfg")
            os.environ["XDG_DATA_HOME"] = str(Path(tmpdir) / "data")
            client = _PreindexClient()
            service = MMWikiService(
                Context(client=client, server="http://x", profile="p", output_json=True)
            )
            result = service.preindex_documents(document_ids=["1", "2", "3", "1", "8"], workers=3)
            self.assertEqual(result["requested_count"], 5)
            self.assertEqual(result["resolved_count"], 4)
            self.assertEqual(result["indexed_count"], 2)
            self.assertEqual(result["skipped_count"], 1)
            self.assertEqual(result["failed_count"], 1)
            self.assertEqual(len(result["errors"]), 2)

            docs = service.index.get_documents_by_ids(
                server="http://x",
                profile="p",
                document_ids=["1", "2", "3", "8"],
            )
            self.assertEqual(set(docs.keys()), {"1", "2"})

    def test_preindex_documents_summary_is_worker_deterministic(self) -> None:
        with TemporaryDirectory() as tmpdir:
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmpdir) / "cfg")
            os.environ["XDG_DATA_HOME"] = str(Path(tmpdir) / "data")
            client = _PreindexClient()
            service = MMWikiService(
                Context(client=client, server="http://x", profile="p", output_json=True)
            )
            inputs = ["1", "2", "3", "8", "1"]
            one_worker = service.preindex_documents(document_ids=inputs, workers=1)
            many_workers = service.preindex_documents(document_ids=inputs, workers=5)
            self.assertEqual(one_worker["requested_count"], many_workers["requested_count"])
            self.assertEqual(one_worker["resolved_count"], many_workers["resolved_count"])
            self.assertEqual(one_worker["indexed_count"], many_workers["indexed_count"])
            self.assertEqual(one_worker["skipped_count"], many_workers["skipped_count"])
            self.assertEqual(one_worker["failed_count"], many_workers["failed_count"])

    def test_space_tree_returns_ordered_documents_and_counts(self) -> None:
        with TemporaryDirectory() as tmpdir:
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmpdir) / "cfg")
            os.environ["XDG_DATA_HOME"] = str(Path(tmpdir) / "data")
            client = _SpaceClient()
            service = MMWikiService(
                Context(client=client, server="http://x", profile="p", output_json=True)
            )
            result = service.space_tree(space_id="10")
            self.assertEqual(result["space_id"], "10")
            self.assertEqual(result["root_document_id"], "1000")
            self.assertEqual(
                result["documents"],
                [
                    {"document_id": "1000", "title": "研发首页"},
                    {"document_id": "1001", "title": "平台规范"},
                    {"document_id": "1002", "title": ""},
                ],
            )
            self.assertEqual(result["document_count"], 3)
            self.assertEqual(result["errors"], [])

    def test_space_tree_includes_root_when_missing_in_payload(self) -> None:
        with TemporaryDirectory() as tmpdir:
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmpdir) / "cfg")
            os.environ["XDG_DATA_HOME"] = str(Path(tmpdir) / "data")
            client = _SpaceClient()
            service = MMWikiService(
                Context(client=client, server="http://x", profile="p", output_json=True)
            )
            result = service.space_tree(space_id="20")
            self.assertEqual(result["documents"][0]["document_id"], "2000")
            self.assertTrue(any("root document missing" in item for item in result["errors"]))

    def test_space_valid_list_collects_valid_and_invalid(self) -> None:
        with TemporaryDirectory() as tmpdir:
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmpdir) / "cfg")
            os.environ["XDG_DATA_HOME"] = str(Path(tmpdir) / "data")
            client = _SpaceClient()
            service = MMWikiService(
                Context(client=client, server="http://x", profile="p", output_json=True)
            )
            result = service.space_list_valid(max_pages=5)
            self.assertEqual(
                result["spaces"],
                [
                    {"space_id": "10", "space_name": "研发空间", "root_document_id": "1000"},
                    {"space_id": "11", "space_name": "产品空间", "root_document_id": "1100"},
                ],
            )
            self.assertEqual(result["valid_count"], 2)
            self.assertEqual(result["invalid_count"], 1)
            self.assertEqual(result["errors"][0]["space_id"], "12")


if __name__ == "__main__":
    unittest.main()
