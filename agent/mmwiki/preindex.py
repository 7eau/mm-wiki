from __future__ import annotations

import argparse
import json
import sys

from .client import MMWikiClient
from .core import Context, MMWikiService
from .errors import MMWikiError
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
    if isinstance(value, dict):
        for key, val in value.items():
            print(f"{key}: {val}")
        return
    print(value)


def _parse_id_csv(value: str, *, flag_name: str) -> list[str]:
    ids = [item.strip() for item in value.split(",") if item.strip()]
    if not ids:
        raise ValueError(f"{flag_name} requires at least one id")
    return ids


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mmwiki-preindex")
    parser.add_argument("--server", default=None, help="MM-Wiki server base URL")
    parser.add_argument("--profile", default="default", help="local profile alias")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--document-ids", default="", help="comma-separated document ids")
    parser.add_argument("--space-ids", default="", help="comma-separated space ids")
    parser.add_argument("--doc-range-start", type=int, default=None, help="inclusive document id range start")
    parser.add_argument("--doc-range-end", type=int, default=None, help="inclusive document id range end")
    parser.add_argument("--workers", type=int, default=4, help="parallel worker count")
    return parser


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdio()
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        document_ids = (
            _parse_id_csv(args.document_ids, flag_name="--document-ids") if args.document_ids else []
        )
        space_ids = _parse_id_csv(args.space_ids, flag_name="--space-ids") if args.space_ids else []
        has_doc_range = args.doc_range_start is not None or args.doc_range_end is not None
        if not document_ids and not space_ids and not has_doc_range:
            raise ValueError(
                "at least one source is required: --document-ids, --space-ids, or doc range flags"
            )

        server = resolve_server(args.profile, args.server)
        client = MMWikiClient(server=server, profile=args.profile)
        ctx = Context(client=client, server=server, profile=args.profile, output_json=args.json)
        service = MMWikiService(ctx)

        resolve_result = service.resolve_preindex_document_ids(
            document_ids=document_ids,
            space_ids=space_ids,
            doc_range_start=args.doc_range_start,
            doc_range_end=args.doc_range_end,
        )
        preindex_result = service.preindex_documents(
            document_ids=resolve_result["resolved_document_ids"],
            workers=args.workers,
        )
        preindex_result["requested_count"] = int(resolve_result["requested_count"])
        preindex_result["resolved_count"] = int(resolve_result["resolved_count"])
        preindex_result["errors"] = [*resolve_result["errors"], *preindex_result["errors"]]
        _print(preindex_result, args.json)
        return 0
    except MMWikiError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
