from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent.mmwiki.core import Context, MMWikiService
from agent.mmwiki.state import save_profile


class _Resp:
    def __init__(self, *, text: str = "", parsed=None, json=None) -> None:
        self.text = text
        self.parsed = parsed
        self.json = json


class _MockClient:
    def __init__(self) -> None:
        self.authed = False
        self.docs = {"1": {"name": "Home", "content": "# Home"}}
        self.attachments: dict[str, list[tuple[str, str]]] = {}
        self.next_doc = 2

    def clear_session(self) -> None:
        self.authed = False

    def _require_auth(self) -> None:
        if not self.authed:
            from agent.mmwiki.errors import AuthenticationError

            raise AuthenticationError("session expired or not authenticated")

    def get(self, path: str):
        if path.startswith("/author/logout"):
            self.authed = False
            return _Resp(text="")
        self._require_auth()
        if path.startswith("/system/profile/info"):
            return _Resp(
                text="""
                <label>用户名</label><span>admin</span>
                <label>姓名</label><span>管理员</span>
                <label>邮箱</label><span>a@b.com</span>
                <label>手机</label><span>1</span>
                <label>电话</label><span>2</span>
                <label>部门</label><span>d</span>
                <label>职位</label><span>p</span>
                <label>位置</label><span>l</span>
                <label>IM</label><span>im</span>
                """
            )
        if path.startswith("/space/list"):
            return _Resp(text='<a href="/space/document?space_id=10"><strong>研发</strong></a>')
        if path.startswith("/page/view"):
            doc_id = path.split("document_id=", 1)[1]
            doc = self.docs[doc_id]
            return _Resp(
                text=f'<h3 class="view-page-title">{doc["name"]}</h3>'
                f'<div id="document_page_view"><textarea>{doc["content"]}</textarea></div>'
            )
        if path.startswith("/main/search"):
            keyword = path.split("keyword=", 1)[1]
            html = "\n".join(
                f'<a href="/document/index?document_id={doc_id}">{item["name"]}</a>'
                for doc_id, item in self.docs.items()
                if keyword in item["name"]
            )
            return _Resp(text=html)
        if path.startswith("/system/profile/followDoc"):
            return _Resp(text='<a href="/document/index?document_id=1"><i class="fa fa-file-o"></i> Home </a>')
        if path.startswith("/system/profile/activity"):
            return _Resp(
                text="""
                <tr><td>创建</td><td><a href="/document/index?document_id=1">Home</a></td><td>init</td><td>2026-01-01</td></tr>
                <tr><td>修改</td><td><a href="/document/index?document_id=1">Home</a></td><td>edit</td><td>2026-01-02</td></tr>
                """
            )
        if path.startswith("/attachment/page"):
            doc_id = path.split("document_id=", 1)[1]
            rows = []
            for aid, name in self.attachments.get(doc_id, []):
                rows.append(f'<td>{name}</td><td><a href="/attachment/download?attachment_id={aid}">d</a></td>')
            return _Resp(text="\n".join(rows))
        raise ValueError(path)

    def post(self, path: str, data):
        if path == "/author/login":
            self.authed = True
            return _Resp(parsed={"ok": True, "message": "登录成功", "redirect": {"url": "/main/index"}})
        self._require_auth()
        if path == "/document/save":
            doc_id = str(self.next_doc)
            self.next_doc += 1
            self.docs[doc_id] = {"name": data["name"], "content": ""}
            return _Resp(parsed={"ok": True, "redirect": {"url": f"/document/index?document_id={doc_id}"}})
        if path == "/page/modify":
            doc_id = data["document_id"]
            self.docs[doc_id]["name"] = data["name"]
            self.docs[doc_id]["content"] = data["document_page_editor-markdown-doc"]
            return _Resp(parsed={"ok": True, "redirect": {"url": f"/document/index?document_id={doc_id}"}})
        raise ValueError(path)

    def upload_file(self, path: str, *, field: str, file_path: str, extra_fields=None):
        self._require_auth()
        if field == "editormd-image-file":
            doc_id = path.split("document_id=", 1)[1]
            return _Resp(json={"success": 1, "url": f"/images/10/{doc_id}/a.png"})
        doc_id = path.split("document_id=", 1)[1]
        existing = self.attachments.setdefault(doc_id, [])
        aid = str(len(existing) + 1)
        existing.append((aid, Path(file_path).name))
        return _Resp(parsed={"ok": True})


class IntegrationTests(unittest.TestCase):
    def test_login_logout_status_and_doc_flows(self) -> None:
        with TemporaryDirectory() as tmpdir:
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmpdir) / "cfg")
            os.environ["XDG_DATA_HOME"] = str(Path(tmpdir) / "data")
            save_profile("it", "http://mock")
            client = _MockClient()
            service = MMWikiService(Context(client=client, server="http://mock", profile="it", output_json=True))

            service.auth_login("admin", "pass")
            info = service.auth_status()
            self.assertEqual(info["username"], "admin")

            md = Path(tmpdir) / "new.md"
            (Path(tmpdir) / "a.png").write_bytes(b"img")
            (Path(tmpdir) / "doc.pdf").write_bytes(b"pdf")
            md.write_text("![a](a.png)\n[file](doc.pdf)\ncontent", encoding="utf-8")

            created = service.doc_add(
                name="DocA",
                parent_id="1",
                space_id=None,
                space_name="研发",
                doc_type=1,
                from_md=str(md),
                comment="create",
            )
            doc_id = created["document_id"]
            self.assertTrue(doc_id)

            pulled_path = Path(tmpdir) / "pull.md"
            service.doc_pull(document_id=doc_id, md_path=str(pulled_path))
            pulled_path.write_text("# changed", encoding="utf-8")
            service.doc_push(document_id=doc_id, md_path=str(pulled_path), force=True, comment="push")

            self.assertTrue(any(item["document_id"] == doc_id for item in service.search_title(keyword="DocA")))
            self.assertTrue(service.search_content(keyword="changed"))
            self.assertTrue(service.user_follows())
            acts = service.user_activity()
            self.assertTrue(any(item["is_published"] for item in acts))
            self.assertTrue(any(item["is_edited"] for item in acts))

            service.auth_logout()
            from agent.mmwiki.errors import AuthenticationError

            with self.assertRaises(AuthenticationError):
                service.auth_status()


if __name__ == "__main__":
    unittest.main()
