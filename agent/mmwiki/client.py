from __future__ import annotations

import json
import mimetypes
import os
import uuid
from dataclasses import dataclass
from http.cookiejar import MozillaCookieJar
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

from .errors import ApiError, AuthenticationError
from .parsing import classify_response, is_login_redirect, parse_html_error, parse_json_response
from .paths import data_dir, ensure_dirs


@dataclass
class Response:
    kind: str
    status: int
    url: str
    headers: dict[str, str]
    text: str
    json: dict[str, Any] | None
    parsed: dict[str, Any] | None


def _multipart_form(parts: list[tuple[str, str, bytes, str]]) -> tuple[bytes, str]:
    boundary = f"----mmwiki-{uuid.uuid4().hex}"
    lines: list[bytes] = []
    for field, filename, content, content_type in parts:
        lines.append(f"--{boundary}\r\n".encode())
        lines.append(
            f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'.encode()
        )
        lines.append(f"Content-Type: {content_type}\r\n\r\n".encode())
        lines.append(content)
        lines.append(b"\r\n")
    lines.append(f"--{boundary}--\r\n".encode())
    body = b"".join(lines)
    return body, f"multipart/form-data; boundary={boundary}"


class MMWikiClient:
    def __init__(self, server: str, profile: str, timeout: int = 20) -> None:
        ensure_dirs()
        self.server = server.rstrip("/")
        self.profile = profile
        self.timeout = timeout
        self.cookie_file = data_dir() / "cookies" / f"{profile}.cookies.txt"
        self.jar = MozillaCookieJar(str(self.cookie_file))
        if self.cookie_file.exists():
            self.jar.load(ignore_discard=True, ignore_expires=True)
        self.opener = build_opener(HTTPCookieProcessor(self.jar))

    def _save_cookies(self) -> None:
        self.cookie_file.parent.mkdir(parents=True, exist_ok=True)
        self.jar.save(ignore_discard=True, ignore_expires=True)

    def request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        raw_body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        url = f"{self.server}{path if path.startswith('/') else '/' + path}"
        request_headers = {"User-Agent": "mmwiki-cli/0.1"}
        if headers:
            request_headers.update(headers)
        payload = raw_body
        if data is not None:
            payload = urlencode({k: str(v) for k, v in data.items()}).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        req = Request(url, data=payload, method=method.upper(), headers=request_headers)
        try:
            with self.opener.open(req, timeout=self.timeout) as resp:
                body = resp.read()
                status = resp.getcode()
                final_url = resp.geturl()
                response_headers = dict(resp.headers.items())
        except HTTPError as exc:
            body = exc.read()
            status = exc.code
            final_url = exc.geturl()
            response_headers = dict(exc.headers.items()) if exc.headers else {}
        text = body.decode("utf-8", errors="replace")
        kind = classify_response(response_headers.get("Content-Type", ""), text)
        parsed_json: dict[str, Any] | None = None
        parsed: dict[str, Any] | None = None
        if kind == "json":
            try:
                parsed_json = json.loads(text)
                parsed = parse_json_response(parsed_json)
            except json.JSONDecodeError:
                kind = "text"
        if is_login_redirect(final_url, text):
            raise AuthenticationError("session expired or not authenticated")
        if kind == "html":
            err = parse_html_error(text)
            if err:
                raise ApiError(err)
        if parsed and not parsed["ok"]:
            raise ApiError(str(parsed.get("message", "request failed")))
        self._save_cookies()
        return Response(
            kind=kind,
            status=status,
            url=final_url,
            headers=response_headers,
            text=text,
            json=parsed_json,
            parsed=parsed,
        )

    def get(self, path: str) -> Response:
        return self.request("GET", path)

    def post(self, path: str, data: dict[str, Any]) -> Response:
        return self.request("POST", path, data=data)

    def upload_file(
        self,
        path: str,
        *,
        field: str,
        file_path: str,
        extra_fields: dict[str, Any] | None = None,
    ) -> Response:
        final_path = Path(file_path)
        if not final_path.exists():
            raise FileNotFoundError(file_path)
        content = final_path.read_bytes()
        ctype, _ = mimetypes.guess_type(final_path.name)
        ctype = ctype or "application/octet-stream"
        body_parts: list[tuple[str, str, bytes, str]] = [(field, final_path.name, content, ctype)]
        body, content_type = _multipart_form(body_parts)
        if extra_fields:
            prefix = []
            boundary = content_type.split("boundary=", 1)[1]
            for key, value in extra_fields.items():
                prefix.append(f"--{boundary}\r\n".encode())
                prefix.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
                prefix.append(str(value).encode())
                prefix.append(b"\r\n")
            body = b"".join(prefix) + body
        return self.request(
            "POST",
            path,
            raw_body=body,
            headers={"Content-Type": content_type, "Content-Length": str(len(body))},
        )

    def clear_session(self) -> None:
        if self.cookie_file.exists():
            os.remove(self.cookie_file)
        self.jar.clear()

