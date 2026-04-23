from __future__ import annotations

import os
from typing import Any

from .client import MMWikiClient
from .core import Context, MMWikiService
from .state import resolve_server


def _service(server: str | None, profile: str) -> MMWikiService:
    resolved = resolve_server(profile, server)
    client = MMWikiClient(server=resolved, profile=profile)
    return MMWikiService(Context(client=client, server=resolved, profile=profile, output_json=True))


def main() -> int:
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception:
        raise SystemExit(
            "mcp SDK not found. Install with: pip install mcp\n"
            "Then run: python -m agent.mmwiki.mcp_server"
        )

    mcp = FastMCP("mmwiki")

    @mcp.tool()
    def auth_login(username: str, password: str, profile: str = "default", server: str | None = None, sso: bool = False) -> dict[str, Any]:
        return _service(server, profile).auth_login(username, password, sso)

    @mcp.tool()
    def auth_logout(profile: str = "default", server: str | None = None) -> dict[str, Any]:
        return _service(server, profile).auth_logout()

    @mcp.tool()
    def auth_status(profile: str = "default", server: str | None = None) -> dict[str, Any]:
        return _service(server, profile).auth_status()

    @mcp.tool()
    def doc_pull(document_id: str, md_path: str, profile: str = "default", server: str | None = None) -> dict[str, Any]:
        return _service(server, profile).doc_pull(document_id=document_id, md_path=md_path)

    @mcp.tool()
    def doc_push(
        document_id: str,
        md_path: str,
        force: bool = False,
        comment: str = "updated via MCP",
        profile: str = "default",
        server: str | None = None,
    ) -> dict[str, Any]:
        return _service(server, profile).doc_push(
            document_id=document_id, md_path=md_path, force=force, comment=comment
        )

    @mcp.tool()
    def doc_add(
        name: str,
        parent_id: str,
        space_id: str | None = None,
        space_name: str | None = None,
        doc_type: int = 1,
        from_md: str | None = None,
        comment: str = "added via MCP",
        profile: str = "default",
        server: str | None = None,
    ) -> dict[str, Any]:
        return _service(server, profile).doc_add(
            name=name,
            parent_id=parent_id,
            space_id=space_id,
            space_name=space_name,
            doc_type=doc_type,
            from_md=from_md,
            comment=comment,
        )

    @mcp.tool()
    def search_title(keyword: str, profile: str = "default", server: str | None = None) -> list[dict[str, str]]:
        return _service(server, profile).search_title(keyword=keyword)

    @mcp.tool()
    def search_content(keyword: str, profile: str = "default", server: str | None = None) -> list[dict[str, str]]:
        return _service(server, profile).search_content(keyword=keyword)

    @mcp.tool()
    def user_info(profile: str = "default", server: str | None = None) -> dict[str, Any]:
        return _service(server, profile).user_info()

    @mcp.tool()
    def user_follows(profile: str = "default", server: str | None = None) -> list[dict[str, str]]:
        return _service(server, profile).user_follows()

    @mcp.tool()
    def user_activity(keyword: str = "", profile: str = "default", server: str | None = None) -> list[dict[str, str]]:
        return _service(server, profile).user_activity(keyword=keyword)

    transport = os.environ.get("MMWIKI_MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

