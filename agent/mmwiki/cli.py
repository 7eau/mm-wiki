from __future__ import annotations

import argparse
import json
import sys

from .client import MMWikiClient
from .core import Context, MMWikiService
from .errors import MMWikiError
from .index import ContentIndex
from .state import resolve_server


def _ensure_utf8_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8")
            except Exception:
                pass


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


def _parse_document_ids(value: str) -> list[str]:
    ids = [item.strip() for item in value.split(",") if item.strip()]
    if not ids:
        raise ValueError("--document-ids requires at least one id")
    return ids


def _print_analyze_blocks(items: list[dict], *, field: str) -> None:
    if not items:
        print("(empty)")
        return
    for item in items:
        print(f"document_id: {item.get('document_id', '')}")
        print(f"title: {item.get('title', '')}")
        value = item.get(field)
        if isinstance(value, list):
            print(f"{field}: {', '.join(str(v) for v in value)}")
        else:
            print(f"{field}: {value}")
        print("")


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
    delete_local = doc_sub.add_parser("delete-local")
    delete_local.add_argument("--md", required=True)
    delete_local.add_argument("--document-id")

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

    space = subparsers.add_parser("space")
    space_sub = space.add_subparsers(dest="cmd", required=True)
    tree = space_sub.add_parser("tree")
    tree.add_argument("--space-id", required=True)
    valid_list = space_sub.add_parser("valid-list")
    valid_list.add_argument("--max-pages", type=int, default=20)

    analyze = subparsers.add_parser("analyze")
    analyze_sub = analyze.add_subparsers(dest="cmd", required=True)
    summary = analyze_sub.add_parser("summary")
    summary.add_argument("--document-ids", required=True, help="comma-separated document ids")
    summary.add_argument("--max-sentences", type=int, default=3)
    keywords = analyze_sub.add_parser("keywords")
    keywords.add_argument("--document-ids", required=True, help="comma-separated document ids")
    keywords.add_argument("--top-k", type=int, default=8)

    index = subparsers.add_parser("index")
    index_sub = index.add_subparsers(dest="cmd", required=True)
    export = index_sub.add_parser("export")
    export.add_argument("--out", required=True)
    install = index_sub.add_parser("install")
    install.add_argument("--from", dest="from_path", required=True)
    install.add_argument("--backup")
    index_sub.add_parser("preindex-follows-if-missing")
    return parser


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdio()
    parser = _base_parser()
    args = parser.parse_args(argv)
    try:
        if (
            args.group == "index"
            and args.cmd == "preindex-follows-if-missing"
            and ContentIndex.db_path().exists()
        ):
            _print(
                {
                    "requested_count": 0,
                    "resolved_count": 0,
                    "indexed_count": 0,
                    "skipped_count": 0,
                    "failed_count": 0,
                    "errors": [],
                    "skipped_reason": "index_exists",
                },
                args.json,
            )
            return 0

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
            elif args.cmd == "delete-local":
                result = service.doc_delete_local(md_path=args.md, document_id=args.document_id)
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

        if args.group == "analyze":
            document_ids = _parse_document_ids(args.document_ids)
            if args.cmd == "summary":
                result = service.analyze_summary(document_ids=document_ids, max_sentences=args.max_sentences)
                if args.json:
                    _print(result, args.json)
                else:
                    _print_analyze_blocks(result, field="summary")
            else:
                result = service.analyze_keywords(document_ids=document_ids, top_k=args.top_k)
                if args.json:
                    _print(result, args.json)
                else:
                    _print_analyze_blocks(result, field="keywords")
            return 0

        if args.group == "index":
            if args.cmd == "export":
                result = service.index_export(out_path=args.out)
            elif args.cmd == "install":
                result = service.index_install(from_path=args.from_path, backup_path=args.backup)
            else:
                follows = service.user_follows()
                follow_ids = [item["document_id"] for item in follows if item.get("document_id")]
                result = service.preindex_documents(document_ids=follow_ids, workers=4)
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

        if args.group == "space":
            if args.cmd == "tree":
                result = service.space_tree(space_id=args.space_id)
            else:
                result = service.space_list_valid(max_pages=args.max_pages)
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
