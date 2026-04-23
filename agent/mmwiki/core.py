from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from .client import MMWikiClient
from .errors import DriftError
from .index import ContentIndex, IndexedDoc
from .markdown import rewrite_markdown_assets, sha256_text
from .parsing import (
    extract_markdown_from_page,
    extract_page_title,
    parse_profile_activity,
    parse_profile_follow_doc,
    parse_profile_info,
    parse_redirect_document_id,
    parse_search_title,
    parse_space_list,
)
from .state import get_snapshot, set_snapshot


@dataclass
class Context:
    client: MMWikiClient
    server: str
    profile: str
    output_json: bool


class MMWikiService:
    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx
        self.index = ContentIndex()

    def auth_login(self, username: str, password: str, use_sso: bool = False) -> dict:
        path = "/author/authLogin" if use_sso else "/author/login"
        resp = self.ctx.client.post(path, {"username": username, "password": password})
        return resp.parsed or {"ok": True, "message": "登录成功"}

    def auth_logout(self) -> dict:
        self.ctx.client.get("/author/logout")
        self.ctx.client.clear_session()
        return {"ok": True, "message": "已退出"}

    def auth_status(self) -> dict:
        resp = self.ctx.client.get("/system/profile/info")
        return parse_profile_info(resp.text)

    def resolve_space_id(self, *, space_id: str | None, space_name: str | None) -> str:
        if space_id:
            return space_id
        if not space_name:
            raise ValueError("either --space-id or --space-name is required")
        spaces = []
        page = 1
        while page <= 5:
            resp = self.ctx.client.get(f"/space/list?page={page}")
            batch = parse_space_list(resp.text)
            if not batch:
                break
            spaces.extend(batch)
            page += 1
        for space in spaces:
            if space["name"] == space_name:
                return space["space_id"]
        raise ValueError(f"space not found: {space_name}")

    def doc_add(
        self,
        *,
        name: str,
        parent_id: str,
        space_id: str | None,
        space_name: str | None,
        doc_type: int,
        from_md: str | None,
        comment: str,
    ) -> dict:
        resolved_space_id = self.resolve_space_id(space_id=space_id, space_name=space_name)
        resp = self.ctx.client.post(
            "/document/save",
            {
                "space_id": resolved_space_id,
                "parent_id": parent_id,
                "type": doc_type,
                "name": name,
            },
        )
        redirect = (resp.parsed or {}).get("redirect", {}).get("url", "")
        document_id = parse_redirect_document_id(redirect)
        result = {
            "space_id": resolved_space_id,
            "document_id": document_id,
            "name": name,
            "created": True,
        }
        if from_md and document_id:
            self.doc_push(
                document_id=document_id,
                md_path=from_md,
                force=True,
                comment=comment,
                explicit_name=name,
            )
            result["content_uploaded"] = True
        return result

    def _fetch_document_markdown(self, document_id: str) -> tuple[str, str]:
        resp = self.ctx.client.get(f"/page/view?document_id={quote(document_id)}")
        content = extract_markdown_from_page(resp.text)
        title = extract_page_title(resp.text)
        return content, title

    def doc_pull(self, *, document_id: str, md_path: str) -> dict:
        content, title = self._fetch_document_markdown(document_id)
        path = Path(md_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        digest = sha256_text(content)
        set_snapshot(self.ctx.server, self.ctx.profile, document_id, str(path), digest, title)
        self.index.upsert(
            server=self.ctx.server,
            profile=self.ctx.profile,
            doc=IndexedDoc(document_id=document_id, title=title or document_id, content=content, md_path=str(path)),
        )
        return {"document_id": document_id, "md_path": str(path), "sha256": digest, "title": title}

    def doc_push(
        self,
        *,
        document_id: str,
        md_path: str,
        force: bool,
        comment: str,
        explicit_name: str | None = None,
    ) -> dict:
        path = Path(md_path)
        content = path.read_text(encoding="utf-8")
        remote_content, remote_title = self._fetch_document_markdown(document_id)
        remote_digest = sha256_text(remote_content)
        local_snapshot = get_snapshot(self.ctx.server, self.ctx.profile, document_id, str(path))
        if not force and local_snapshot and local_snapshot.get("sha256") != remote_digest:
            raise DriftError("remote content changed since last pull; retry with --force")
        rewritten = rewrite_markdown_assets(self.ctx.client, document_id, content, str(path))
        new_name = explicit_name or remote_title or document_id
        self.ctx.client.post(
            "/page/modify",
            {
                "document_id": document_id,
                "name": new_name,
                "document_page_editor-markdown-doc": rewritten,
                "comment": comment,
                "is_notice_user": "0",
                "is_follow_doc": "0",
            },
        )
        new_digest = sha256_text(rewritten)
        set_snapshot(self.ctx.server, self.ctx.profile, document_id, str(path), new_digest, new_name)
        self.index.upsert(
            server=self.ctx.server,
            profile=self.ctx.profile,
            doc=IndexedDoc(document_id=document_id, title=new_name, content=rewritten, md_path=str(path)),
        )
        return {"document_id": document_id, "md_path": str(path), "sha256": new_digest, "title": new_name}

    def doc_edit(self, *, md_path: str) -> dict:
        editor = os.environ.get("EDITOR", "vi")
        os.system(f'{editor} "{md_path}"')
        return {"edited": True, "editor": editor, "md_path": md_path}

    def search_title(self, *, keyword: str) -> list[dict[str, str]]:
        resp = self.ctx.client.get(f"/main/search?search_type=title&keyword={quote(keyword)}")
        return parse_search_title(resp.text)

    def search_content(self, *, keyword: str) -> list[dict[str, str]]:
        return self.index.search(server=self.ctx.server, profile=self.ctx.profile, keyword=keyword)

    def user_info(self) -> dict:
        resp = self.ctx.client.get("/system/profile/info")
        return parse_profile_info(resp.text)

    def user_follows(self) -> list[dict[str, str]]:
        resp = self.ctx.client.get("/system/profile/followDoc")
        return parse_profile_follow_doc(resp.text)

    def user_activity(self, *, keyword: str = "") -> list[dict[str, str]]:
        path = "/system/profile/activity"
        if keyword:
            path += f"?keyword={quote(keyword)}"
        resp = self.ctx.client.get(path)
        return parse_profile_activity(resp.text)

