from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import quote

from .client import MMWikiClient
from .errors import ApiError
from .parsing import parse_attachment_download_url


_RE_MD_LINK = re.compile(r"(!?\[[^\]]*\])\(([^)]+)\)")
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}


def sha256_text(content: str) -> str:
    import hashlib

    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def rewrite_markdown_assets(client: MMWikiClient, document_id: str, markdown: str, md_path: str) -> str:
    base = Path(md_path).resolve().parent

    def replace(match: re.Match[str]) -> str:
        label, target = match.group(1), match.group(2).strip()
        if target.startswith(("http://", "https://", "/", "#")):
            return match.group(0)
        local_file = (base / target).resolve()
        if not local_file.exists() or not local_file.is_file():
            return match.group(0)
        ext = local_file.suffix.lower()
        if ext in _IMAGE_EXTS:
            resp = client.upload_file(
                f"/image/upload?document_id={quote(document_id)}",
                field="editormd-image-file",
                file_path=str(local_file),
            )
            if not resp.json or resp.json.get("success") != 1:
                raise ApiError(f"image upload failed: {local_file}")
            return f"{label}({resp.json.get('url', '')})"
        resp = client.upload_file(
            f"/attachment/upload?document_id={quote(document_id)}",
            field="attachment",
            file_path=str(local_file),
        )
        if not resp.parsed:
            raise ApiError(f"attachment upload failed: {local_file}")
        list_resp = client.get(f"/attachment/page?document_id={quote(document_id)}")
        url = parse_attachment_download_url(list_resp.text, os.path.basename(local_file))
        if not url:
            raise ApiError(f"uploaded attachment not found in list: {local_file}")
        return f"{label}({url})"

    return _RE_MD_LINK.sub(replace, markdown)
