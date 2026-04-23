from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

from agent.mmwiki import cli as cli_module
from agent.mmwiki.cli import _base_parser, _parse_document_ids
from agent.mmwiki.preindex import _build_parser as _build_preindex_parser


class CLITests(unittest.TestCase):
    def test_index_parser(self) -> None:
        parser = _base_parser()
        export = parser.parse_args(["index", "export", "--out", "./content.db"])
        self.assertEqual(export.group, "index")
        self.assertEqual(export.cmd, "export")
        self.assertEqual(export.out, "./content.db")

        install = parser.parse_args(
            ["index", "install", "--from", "./other.db", "--backup", "./bak.db"]
        )
        self.assertEqual(install.group, "index")
        self.assertEqual(install.cmd, "install")
        self.assertEqual(install.from_path, "./other.db")
        self.assertEqual(install.backup, "./bak.db")

        preindex = parser.parse_args(["index", "preindex-follows-if-missing"])
        self.assertEqual(preindex.group, "index")
        self.assertEqual(preindex.cmd, "preindex-follows-if-missing")

    def test_doc_delete_local_parser(self) -> None:
        parser = _base_parser()
        args = parser.parse_args(["doc", "delete-local", "--md", "./a.md", "--document-id", "9"])
        self.assertEqual(args.group, "doc")
        self.assertEqual(args.cmd, "delete-local")
        self.assertEqual(args.md, "./a.md")
        self.assertEqual(args.document_id, "9")

    def test_analyze_parsers(self) -> None:
        parser = _base_parser()
        summary = parser.parse_args(
            ["analyze", "summary", "--document-ids", "1,2,3", "--max-sentences", "2"]
        )
        self.assertEqual(summary.group, "analyze")
        self.assertEqual(summary.cmd, "summary")
        self.assertEqual(summary.max_sentences, 2)

        keywords = parser.parse_args(["analyze", "keywords", "--document-ids", "7", "--top-k", "5"])
        self.assertEqual(keywords.group, "analyze")
        self.assertEqual(keywords.cmd, "keywords")
        self.assertEqual(keywords.top_k, 5)

    def test_parse_document_ids(self) -> None:
        self.assertEqual(_parse_document_ids("1,2, 3"), ["1", "2", "3"])
        with self.assertRaises(ValueError):
            _parse_document_ids(" , ")

    def test_standalone_preindex_parser(self) -> None:
        parser = _build_preindex_parser()
        args = parser.parse_args(
            [
                "--document-ids",
                "1,2",
                "--space-ids",
                "10,20",
                "--doc-range-start",
                "100",
                "--doc-range-end",
                "110",
                "--workers",
                "8",
            ]
        )
        self.assertEqual(args.document_ids, "1,2")
        self.assertEqual(args.space_ids, "10,20")
        self.assertEqual(args.doc_range_start, 100)
        self.assertEqual(args.doc_range_end, 110)
        self.assertEqual(args.workers, 8)

    def test_preindex_follows_if_missing_skips_when_index_exists(self) -> None:
        with TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "content.db"
            index_path.write_text("x", encoding="utf-8")
            with patch.object(cli_module.ContentIndex, "db_path", return_value=index_path):
                with patch.object(cli_module, "_print") as print_mock:
                    code = cli_module.main(["--json", "index", "preindex-follows-if-missing"])
            self.assertEqual(code, 0)
            print_mock.assert_called_once()
            payload = print_mock.call_args.args[0]
            self.assertEqual(payload["skipped_reason"], "index_exists")

    def test_preindex_follows_if_missing_runs_when_index_missing(self) -> None:
        with TemporaryDirectory() as tmpdir:
            missing = Path(tmpdir) / "content.db"

            class _FakeService:
                def user_follows(self):
                    return [{"document_id": "11"}, {"document_id": "12"}, {"document_id": "11"}]

                def preindex_documents(self, *, document_ids, workers):
                    self.received = (document_ids, workers)
                    return {
                        "requested_count": 3,
                        "resolved_count": 2,
                        "indexed_count": 2,
                        "skipped_count": 0,
                        "failed_count": 0,
                        "errors": [],
                    }

            with patch.object(cli_module.ContentIndex, "db_path", return_value=missing):
                with patch.object(cli_module, "resolve_server", return_value="http://x"):
                    with patch.object(cli_module, "MMWikiClient"):
                        with patch.object(cli_module, "MMWikiService", return_value=_FakeService()):
                            with patch.object(cli_module, "_print") as print_mock:
                                code = cli_module.main(["index", "preindex-follows-if-missing"])
            self.assertEqual(code, 0)
            payload = print_mock.call_args.args[0]
            self.assertEqual(payload["indexed_count"], 2)


if __name__ == "__main__":
    unittest.main()
