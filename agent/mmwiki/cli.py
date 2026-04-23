from __future__ import annotations

import argparse
import json
import sys

from .client import MMWikiClient
from .core import Context, MMWikiService
from .errors import MMWikiError
from .state import resolve_server


def _print(value, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return
    if isinstance(value, list):
        for item in value:
            print(" | ".join(f"{k}={v}" for k, v in item.items()))
        if not value:
            print("(empty)")
        return
    if isinstance(value, dict):
        for key, val in value.items():
            print(f"{key}: {val}")
        return
    print(value)


def _base_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mmwiki")
    parser.add_argument("--server", default=None, help="MM-Wiki server base URL")
    parser.add_argument("--profile", default="default", help="local profile alias")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    subparsers = parser.add_subparsers(dest="group", required=True)

    auth = subparsers.add_parser("auth")
    auth_sub = auth.add_subparsers(dest="cmd", required=True)
    login = auth_sub.add_parser("login")
    login.add_argument("--username", required=True)
    login.add_argument("--password", required=True)
    login.add_argument("--sso", action="store_true")
    auth_sub.add_parser("logout")
    auth_sub.add_parser("status")

    doc = subparsers.add_parser("doc")
    doc_sub = doc.add_subparsers(dest="cmd", required=True)
    add = doc_sub.add_parser("add")
    add.add_argument("--name", required=True)
    add.add_argument("--space-id")
    add.add_argument("--space-name")
    add.add_argument("--parent-id", required=True)
    add.add_argument("--type", type=int, default=1, choices=[1, 2])
    add.add_argument("--from-md")
    add.add_argument("--comment", default="added via mmwiki")

    pull = doc_sub.add_parser("pull")
    pull.add_argument("--document-id", required=True)
    pull.add_argument("--md", required=True)

    edit = doc_sub.add_parser("edit")
    edit.add_argument("--md", required=True)

    push = doc_sub.add_parser("push")
    push.add_argument("--document-id", required=True)
    push.add_argument("--md", required=True)
    push.add_argument("--force", action="store_true")
    push.add_argument("--comment", default="updated via mmwiki")

    search = subparsers.add_parser("search")
    search_sub = search.add_subparsers(dest="cmd", required=True)
    s_title = search_sub.add_parser("title")
    s_title.add_argument("keyword")
    s_content = search_sub.add_parser("content")
    s_content.add_argument("keyword")

    user = subparsers.add_parser("user")
    user_sub = user.add_subparsers(dest="cmd", required=True)
    user_sub.add_parser("info")
    user_sub.add_parser("follows")
    activity = user_sub.add_parser("activity")
    activity.add_argument("--keyword", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _base_parser()
    args = parser.parse_args(argv)
    try:
        server = resolve_server(args.profile, args.server)
        client = MMWikiClient(server=server, profile=args.profile)
        ctx = Context(client=client, server=server, profile=args.profile, output_json=args.json)
        service = MMWikiService(ctx)

        if args.group == "auth":
            if args.cmd == "login":
                result = service.auth_login(args.username, args.password, args.sso)
            elif args.cmd == "logout":
                result = service.auth_logout()
            else:
                result = service.auth_status()
            _print(result, args.json)
            return 0

        if args.group == "doc":
            if args.cmd == "add":
                result = service.doc_add(
                    name=args.name,
                    parent_id=args.parent_id,
                    space_id=args.space_id,
                    space_name=args.space_name,
                    doc_type=args.type,
                    from_md=args.from_md,
                    comment=args.comment,
                )
            elif args.cmd == "pull":
                result = service.doc_pull(document_id=args.document_id, md_path=args.md)
            elif args.cmd == "edit":
                result = service.doc_edit(md_path=args.md)
            else:
                result = service.doc_push(
                    document_id=args.document_id,
                    md_path=args.md,
                    force=args.force,
                    comment=args.comment,
                )
            _print(result, args.json)
            return 0

        if args.group == "search":
            if args.cmd == "title":
                result = service.search_title(keyword=args.keyword)
            else:
                result = service.search_content(keyword=args.keyword)
            _print(result, args.json)
            return 0

        if args.group == "user":
            if args.cmd == "info":
                result = service.user_info()
            elif args.cmd == "follows":
                result = service.user_follows()
            else:
                result = service.user_activity(keyword=args.keyword)
            _print(result, args.json)
            return 0
    except MMWikiError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

