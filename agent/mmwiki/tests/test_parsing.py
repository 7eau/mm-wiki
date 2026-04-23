from __future__ import annotations

import unittest

from agent.mmwiki.parsing import (
    classify_response,
    parse_document_tree_ids,
    extract_markdown_from_page,
    is_login_redirect,
    parse_attachment_download_url,
    parse_html_error,
)


class ParsingTests(unittest.TestCase):
    def test_classify_response(self) -> None:
        self.assertEqual(classify_response("application/json", '{"code":1}'), "json")
        self.assertEqual(classify_response("text/html", "<html></html>"), "html")
        self.assertEqual(classify_response("", "  {\"x\":1}"), "json")

    def test_html_error_and_login_redirect(self) -> None:
        html_error = "<h3>很抱歉，您没有权限访问该页面！</h3>"
        self.assertEqual(parse_html_error(html_error), "您没有权限访问该页面！")
        self.assertTrue(is_login_redirect("http://127.0.0.1/author/index", ""))
        self.assertTrue(is_login_redirect("http://127.0.0.1/main/index", '<form action="/author/login">'))

    def test_extract_markdown_unescape(self) -> None:
        html_text = """
        <div id="document_page_view">
          <textarea style="display:none;"># A &amp; B\n&lt;tag&gt;</textarea>
        </div>
        """
        self.assertEqual(extract_markdown_from_page(html_text), "# A & B\n<tag>")

    def test_parse_attachment_download_url(self) -> None:
        html_text = '<td>file.pdf</td><td><a href="/attachment/download?attachment_id=42">x</a></td>'
        self.assertEqual(
            parse_attachment_download_url(html_text, "file.pdf"),
            "/attachment/download?attachment_id=42",
        )

    def test_parse_document_tree_ids(self) -> None:
        html_text = """
        <script>
        var tree = [
          {"document_id": 101, "name":"A"},
          {"document_id":"102","name":"B"},
        ];
        </script>
        <a href="/document/index?document_id=103">C</a>
        <span>document_id:104</span>
        """
        self.assertEqual(parse_document_tree_ids(html_text), ["103", "101", "102", "104"])


if __name__ == "__main__":
    unittest.main()
