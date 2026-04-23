from __future__ import annotations

import html
import json
import re
from typing import Any
from urllib.parse import parse_qs, urlparse


_RE_JSON_LIKE = re.compile(r"^\s*[\{\[]")
_RE_ERR = re.compile(r"很抱歉，\s*([^<\n]+)")
_RE_LOGIN_FORM = re.compile(r'action="/author/(?:index|login|authLogin)"')
_RE_TEXTAREA = re.compile(
    r'<div[^>]+id="document_page_view"[^>]*>.*?<textarea[^>]*>(.*?)</textarea>',
    flags=re.S | re.I,
)
_RE_SPACE_ROW = re.compile(
    r'href="/space/document\?space_id=(\d+)"[^>]*><strong>([^<]+)</strong>',
    flags=re.I,
)
_RE_PAGE_TITLE = re.compile(r'<h3[^>]*class="view-page-title"[^>]*>(.*?)</h3>', flags=re.S | re.I)
_RE_SEARCH_ROW = re.compile(
    r'href="/document/index\?document_id=(\d+)"[^>]*>(?:.|\n)*?</a>',
    flags=re.I,
)
_RE_ACTIVITY_ROW = re.compile(r"<tr>(.*?)</tr>", flags=re.S | re.I)


def classify_response(content_type: str, body_text: str) -> str:
    content_type = (content_type or "").lower()
    if "application/json" in content_type:
        return "json"
    if "text/html" in content_type:
        return "html"
    if _RE_JSON_LIKE.match(body_text):
        return "json"
    if "<html" in body_text.lower() or "<!doctype" in body_text.lower():
        return "html"
    return "text"


def parse_html_error(body_text: str) -> str | None:
    match = _RE_ERR.search(body_text)
    if not match:
        return None
    return html.unescape(match.group(1)).strip()


def is_login_redirect(final_url: str, body_text: str) -> bool:
    lower_url = final_url.lower()
    if "/author/index" in lower_url:
        return True
    if _RE_LOGIN_FORM.search(body_text):
        return True
    if "<title>mm-wiki login" in body_text.lower():
        return True
    return False


def parse_json_response(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": payload.get("code") == 1,
        "message": payload.get("message"),
        "data": payload.get("data"),
        "redirect": payload.get("redirect", {}),
        "raw": payload,
    }


def extract_markdown_from_page(body_text: str) -> str:
    match = _RE_TEXTAREA.search(body_text)
    if not match:
        raise ValueError("unable to extract markdown from page HTML")
    return html.unescape(match.group(1))


def extract_page_title(body_text: str) -> str:
    match = _RE_PAGE_TITLE.search(body_text)
    if not match:
        return ""
    return html.unescape(re.sub(r"<[^>]+>", "", match.group(1))).strip()


def parse_space_list(body_text: str) -> list[dict[str, str]]:
    spaces: list[dict[str, str]] = []
    for item in _RE_SPACE_ROW.finditer(body_text):
        spaces.append({"space_id": item.group(1), "name": html.unescape(item.group(2)).strip()})
    return spaces


def parse_search_title(body_text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in _RE_SEARCH_ROW.finditer(body_text):
        segment = row.group(0)
        document_id = row.group(1)
        label = re.sub(r"<[^>]+>", "", segment)
        name = html.unescape(label).strip()
        if not name:
            continue
        rows.append({"document_id": document_id, "name": name})
    return rows


def parse_redirect_document_id(redirect_url: str) -> str | None:
    if not redirect_url:
        return None
    query = parse_qs(urlparse(redirect_url).query)
    values = query.get("document_id")
    if not values:
        return None
    return values[0]


def parse_profile_info(body_text: str) -> dict[str, Any]:
    user_fields = {}
    for label in ("用户名", "姓名", "邮箱", "手机", "电话", "部门", "职位", "位置", "IM"):
        pattern = re.compile(rf"<label[^>]*>{label}</label>\s*<span>(.*?)</span>", flags=re.S)
        match = pattern.search(body_text)
        user_fields[label] = html.unescape(match.group(1)).strip() if match else ""
    return {
        "username": user_fields["用户名"],
        "given_name": user_fields["姓名"],
        "email": user_fields["邮箱"],
        "mobile": user_fields["手机"],
        "phone": user_fields["电话"],
        "department": user_fields["部门"],
        "position": user_fields["职位"],
        "location": user_fields["位置"],
        "im": user_fields["IM"],
    }


def parse_profile_follow_doc(body_text: str) -> list[dict[str, str]]:
    rows = []
    for match in re.finditer(r'href="/document/index\?document_id=(\d+)".*?<i class="fa fa-file-o"></i>\s*([^<]+)', body_text, flags=re.S):
        rows.append(
            {
                "document_id": match.group(1),
                "document_name": html.unescape(match.group(2)).strip(),
            }
        )
    return rows


def _strip_tags(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", value)).strip()


def parse_profile_activity(body_text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    rows = _RE_ACTIVITY_ROW.findall(body_text)
    for row in rows:
        tds = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.S | re.I)
        if len(tds) < 4:
            continue
        action = _strip_tags(tds[0])
        doc_segment = tds[1]
        doc_match = re.search(r'document_id=(\d+)', doc_segment)
        document_id = doc_match.group(1) if doc_match else ""
        document_name = _strip_tags(doc_segment)
        comment = _strip_tags(tds[2])
        created_at = _strip_tags(tds[3])
        entries.append(
            {
                "action": action,
                "document_id": document_id,
                "document_name": document_name,
                "comment": comment,
                "created_at": created_at,
                "is_published": action == "创建",
                "is_edited": action == "修改",
            }
        )
    return entries


def parse_attachment_download_url(body_text: str, filename: str) -> str | None:
    pattern = re.compile(
        rf"<td>\s*{re.escape(filename)}\s*</td>(?:.|\n)*?href=\"(/attachment/download\?attachment_id=\d+)\"",
        flags=re.I,
    )
    match = pattern.search(body_text)
    if not match:
        return None
    return match.group(1)


def parse_document_tree_ids(body_text: str) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    patterns = (
        re.compile(r"/document/index\?document_id=(\d+)", flags=re.I),
        re.compile(r'"document_id"\s*:\s*"?(\d+)"?', flags=re.I),
        re.compile(r"\bdocument_id\s*:\s*(\d+)", flags=re.I),
        re.compile(r"""['"]id['"]\s*:\s*(?:parseInt\()?\s*(\d+)\s*\)?""", flags=re.I),
    )
    for pattern in patterns:
        for match in pattern.finditer(body_text):
            document_id = match.group(1)
            if document_id in seen:
                continue
            seen.add(document_id)
            ordered.append(document_id)
    return ordered


def parse_document_tree_nodes(body_text: str) -> list[dict[str, str]]:
    seen: set[str] = set()
    ordered: list[dict[str, str]] = []

    def _clean_title(raw: str) -> str:
        return html.unescape(re.sub(r"<[^>]+>", "", raw or "")).strip()

    def _decode_js_string_literal(value: str) -> str:
        payload = (value or "").strip()
        if len(payload) < 2:
            return payload
        quote_char = payload[0]
        if quote_char not in ("'", '"') or payload[-1] != quote_char:
            return payload
        if quote_char == '"':
            try:
                return str(json.loads(payload))
            except Exception:
                pass
        inner = payload[1:-1]
        inner = inner.replace("\\'", "'").replace('\\"', '"')
        inner = inner.replace("\\n", "\n").replace("\\r", "\r").replace("\\t", "\t")
        inner = inner.replace("\\\\", "\\")
        return inner

    def _extract_document_data_blocks(text: str) -> list[tuple[str, str]]:
        blocks: list[tuple[str, str]] = []
        block_pattern = re.compile(r"var\s+documentData\s*=\s*\{(.*?)\};", flags=re.I | re.S)
        id_pattern = re.compile(r"""['"]id['"]\s*:\s*(?:parseInt\()?\s*(\d+)\s*\)?""", flags=re.I)
        name_pattern = re.compile(
            r"""['"]name['"]\s*:\s*("(?:(?:\\.|[^"])*)"|'(?:(?:\\.|[^'])*)')""",
            flags=re.I | re.S,
        )
        bare_name_pattern = re.compile(r"""['"]name['"]\s*:\s*([^,\n]+)""", flags=re.I | re.S)
        for block in block_pattern.finditer(text):
            segment = block.group(1)
            id_match = id_pattern.search(segment)
            if not id_match:
                continue
            title = ""
            name_match = name_pattern.search(segment)
            if name_match:
                title = _decode_js_string_literal(name_match.group(1))
            else:
                bare_name_match = bare_name_pattern.search(segment)
                if bare_name_match:
                    title = bare_name_match.group(1).strip().strip(",")
            blocks.append((id_match.group(1), title))
        return blocks

    def _append(document_id: str, title: str, *, prefer_non_empty: bool) -> None:
        doc_id = (document_id or "").strip()
        if not doc_id:
            return
        clean_title = _clean_title(title)
        if doc_id in seen:
            if prefer_non_empty and clean_title:
                for item in ordered:
                    if item["document_id"] == doc_id and not item["title"]:
                        item["title"] = clean_title
                        break
            return
        seen.add(doc_id)
        ordered.append({"document_id": doc_id, "title": clean_title})

    anchor_pattern = re.compile(
        r'<a[^>]+href="/document/index\?document_id=(\d+)"[^>]*>(.*?)</a>',
        flags=re.I | re.S,
    )
    for match in anchor_pattern.finditer(body_text):
        _append(match.group(1), match.group(2), prefer_non_empty=True)

    quoted_key_pattern = re.compile(
        r'"document_id"\s*:\s*"?(\d+)"?(?:(?!\{|\}).){0,320}?"(?:title|name|text)"\s*:\s*"([^"]*)"',
        flags=re.I | re.S,
    )
    for match in quoted_key_pattern.finditer(body_text):
        _append(match.group(1), match.group(2), prefer_non_empty=False)

    quoted_key_reverse_pattern = re.compile(
        r'"(?:title|name|text)"\s*:\s*"([^"]*)"(?:.(?!\{|\})){0,320}?"document_id"\s*:\s*"?(\d+)"?',
        flags=re.I | re.S,
    )
    for match in quoted_key_reverse_pattern.finditer(body_text):
        _append(match.group(2), match.group(1), prefer_non_empty=False)

    plain_key_pattern = re.compile(
        r"\bdocument_id\s*:\s*(\d+)(?:(?!\{|\}).){0,320}?\b(?:title|name|text)\s*:\s*['\"]([^'\"]*)['\"]",
        flags=re.I | re.S,
    )
    for match in plain_key_pattern.finditer(body_text):
        _append(match.group(1), match.group(2), prefer_non_empty=False)

    for document_id, title in _extract_document_data_blocks(body_text):
        _append(document_id, title, prefer_non_empty=False)

    ztree_pattern = re.compile(
        r"""['"]id['"]\s*:\s*(?:parseInt\()?\s*(\d+)\s*\)?(?:(?!\{|\}).){0,320}?['"]name['"]\s*:\s*("(?:(?:\\.|[^"])*)"|'(?:(?:\\.|[^'])*)')""",
        flags=re.I | re.S,
    )
    for match in ztree_pattern.finditer(body_text):
        _append(match.group(1), _decode_js_string_literal(match.group(2)), prefer_non_empty=False)

    for document_id in parse_document_tree_ids(body_text):
        _append(document_id, "", prefer_non_empty=False)

    return ordered
