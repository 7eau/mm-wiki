from __future__ import annotations

import unittest

from agent.mmwiki.cli import _base_parser, _parse_document_ids


class CLITests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
