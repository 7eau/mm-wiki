from __future__ import annotations

import unittest

from agent.mmwiki.parsing import (
    classify_response,
    extract_markdown_from_page,
    is_login_redirect,
    parse_attachment_download_url,
    parse_document_tree_ids,
    parse_document_tree_nodes,
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

    def test_parse_document_tree_nodes_prefers_anchor_title_and_fallback(self) -> None:
        html_text = """
        <a href="/document/index?document_id=300"><i class="fa"></i> 研发首页 </a>
        <script>
        var tree = [
          {"document_id":300, "name":"Root from payload"},
          {"document_id":"301","title":"Roadmap"},
          {document_id:302,name:"Spec"}
        ];
        </script>
        <span>document_id:303</span>
        """
        self.assertEqual(
            parse_document_tree_nodes(html_text),
            [
                {"document_id": "300", "title": "研发首页"},
                {"document_id": "301", "title": "Roadmap"},
                {"document_id": "302", "title": "Spec"},
                {"document_id": "303", "title": ""},
            ],
        )

    def test_parse_document_tree_nodes_from_documents_data_payload(self) -> None:
        html_text = """
        <script>
        var documentData = {
            'spaceId': parseInt(5),
            'id': parseInt("500"),
            'pId': parseInt(0),
            'name': "空间首页",
            'open': false,
            'isParent': true
        };
        var documentData = {
            'spaceId': parseInt(5),
            'id': parseInt("501"),
            'pId': parseInt(500),
            'name': "后端规范",
            'open': false,
            'isParent': false
        };
        var documentData = {
            'spaceId': parseInt(5),
            'id': parseInt("502"),
            'pId': parseInt(500),
            'name': "前端规范",
            'open': false,
            'isParent': false
        };
        </script>
        """
        self.assertEqual(parse_document_tree_ids(html_text), ["500", "501", "502"])
        self.assertEqual(
            parse_document_tree_nodes(html_text),
            [
                {"document_id": "500", "title": "空间首页"},
                {"document_id": "501", "title": "后端规范"},
                {"document_id": "502", "title": "前端规范"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
