from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from .client import MMWikiClient
from .errors import ApiError, DriftError
from .index import ContentIndex, IndexedDoc
from .markdown import rewrite_markdown_assets, sha256_text
from .parsing import (
    extract_markdown_from_page,
    extract_page_title,
    parse_document_tree_ids,
    parse_profile_activity,
    parse_profile_follow_doc,
    parse_profile_info,
    parse_redirect_document_id,
    parse_search_title,
    parse_space_list,
)
from .state import get_snapshot, remove_snapshots, set_snapshot

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9\u4e00-\u9fff]+", flags=re.UNICODE)
_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[。！？!?\.])\s+|\n+")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "we",
    "with",
    "你",
    "你们",
    "和",
    "在",
    "是",
    "了",
    "及",
    "与",
    "或",
    "并",
    "一个",
    "我们",
    "他们",
    "她们",
    "它们",
}


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

    def index_export(self, *, out_path: str) -> dict:
        return self.index.export_database(out_path=out_path)

    def index_install(self, *, from_path: str, backup_path: str | None = None) -> dict:
        return self.index.install_database(from_path=from_path, backup_path=backup_path)

    def resolve_preindex_document_ids(
        self,
        *,
        document_ids: list[str] | None = None,
        space_ids: list[str] | None = None,
        doc_range_start: int | None = None,
        doc_range_end: int | None = None,
    ) -> dict[str, int | list[str] | list[str]]:
        explicit_ids = list(document_ids or [])
        final_space_ids = list(space_ids or [])
        range_ids = self._build_doc_range_ids(doc_range_start=doc_range_start, doc_range_end=doc_range_end)
        space_doc_ids, resolve_errors = self._resolve_space_document_ids(final_space_ids)
        requested_count = len(explicit_ids) + len(range_ids) + len(final_space_ids)
        resolved = self._ordered_deduplicate([*explicit_ids, *range_ids, *space_doc_ids])
        return {
            "requested_count": requested_count,
            "resolved_count": len(resolved),
            "resolved_document_ids": resolved,
            "errors": resolve_errors,
        }

    def preindex_documents(self, *, document_ids: list[str], workers: int = 4) -> dict:
        resolved_ids = self._ordered_deduplicate(document_ids)
        final_workers = max(1, workers)
        skipped_count = 0
        failed_count = 0
        indexed_count = 0
        errors: list[str] = []

        def _fetch_single(document_id: str) -> IndexedDoc:
            content, title = self._fetch_document_markdown(document_id)
            return IndexedDoc(
                document_id=document_id,
                title=title or document_id,
                content=content,
                md_path=f"remote://{document_id}",
            )

        with ThreadPoolExecutor(max_workers=final_workers) as executor:
            futures = {executor.submit(_fetch_single, document_id): document_id for document_id in resolved_ids}
            for future in as_completed(futures):
                document_id = futures[future]
                try:
                    doc = future.result()
                    self.index.upsert(server=self.ctx.server, profile=self.ctx.profile, doc=doc)
                    indexed_count += 1
                except (ApiError, ValueError) as exc:
                    skipped_count += 1
                    errors.append(f"document_id={document_id}: skipped: {exc}")
                except Exception as exc:
                    failed_count += 1
                    errors.append(f"document_id={document_id}: failed: {exc}")

        return {
            "requested_count": len(document_ids),
            "resolved_count": len(resolved_ids),
            "indexed_count": indexed_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "errors": errors,
        }

    def doc_delete_local(self, *, md_path: str, document_id: str | None = None) -> dict:
        path = Path(md_path)
        removed_file = False
        if path.exists():
            path.unlink()
            removed_file = True
        path_candidates = {md_path}
        try:
            path_candidates.add(str(path.resolve()))
        except FileNotFoundError:
            pass
        removed_snapshots = 0
        for candidate in path_candidates:
            removed_snapshots += remove_snapshots(
                self.ctx.server,
                self.ctx.profile,
                candidate,
                document_id=document_id,
            )
        return {
            "md_path": md_path,
            "document_id": document_id,
            "removed_file": removed_file,
            "removed_snapshots": removed_snapshots,
            "retained_index": True,
            "removed_index": 0,
        }

    def analyze_summary(self, *, document_ids: list[str], max_sentences: int = 3) -> list[dict]:
        docs = self._get_or_fetch_documents(document_ids)
        results = []
        final_max_sentences = max(1, max_sentences)
        for document_id in document_ids:
            doc = docs.get(document_id)
            if not doc:
                continue
            summary = self._summarize(doc.title, doc.content, final_max_sentences)
            results.append(
                {
                    "document_id": document_id,
                    "title": doc.title,
                    "summary": summary,
                    "max_sentences": final_max_sentences,
                }
            )
        return results

    def analyze_keywords(self, *, document_ids: list[str], top_k: int = 8) -> list[dict]:
        docs = self._get_or_fetch_documents(document_ids)
        results = []
        final_top_k = max(1, top_k)
        for document_id in document_ids:
            doc = docs.get(document_id)
            if not doc:
                continue
            keywords = self._extract_keywords(doc.title, doc.content, final_top_k)
            results.append(
                {
                    "document_id": document_id,
                    "title": doc.title,
                    "keywords": keywords,
                    "top_k": final_top_k,
                }
            )
        return results

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

    def _get_or_fetch_documents(self, document_ids: list[str]) -> dict[str, IndexedDoc]:
        docs = self.index.get_documents_by_ids(
            server=self.ctx.server,
            profile=self.ctx.profile,
            document_ids=document_ids,
        )
        missing_ids = [document_id for document_id in document_ids if document_id not in docs]
        for document_id in missing_ids:
            content, title = self._fetch_document_markdown(document_id)
            doc = IndexedDoc(
                document_id=document_id,
                title=title or document_id,
                content=content,
                md_path=f"remote://{document_id}",
            )
            self.index.upsert(server=self.ctx.server, profile=self.ctx.profile, doc=doc)
            docs[document_id] = doc
        return docs

    def _resolve_space_document_ids(self, space_ids: list[str]) -> tuple[list[str], list[str]]:
        resolved: list[str] = []
        errors: list[str] = []
        for space_id in space_ids:
            try:
                default_document_id = self._resolve_space_default_document_id(space_id)
                if not default_document_id:
                    raise ValueError("space default document id not found")
                resp = self.ctx.client.get(f"/document/index?document_id={quote(default_document_id)}")
                document_ids = parse_document_tree_ids(resp.text)
                if not document_ids:
                    document_ids = [default_document_id]
                resolved.extend(document_ids)
            except Exception as exc:
                errors.append(f"space_id={space_id}: {exc}")
        return resolved, errors

    def _resolve_space_default_document_id(self, space_id: str) -> str | None:
        resp = self.ctx.client.get(f"/space/document?space_id={quote(space_id)}")
        response_url = getattr(resp, "url", "")
        from_url = parse_redirect_document_id(response_url) if response_url else None
        if from_url:
            return from_url
        body_match = re.search(r"/document/index\?document_id=(\d+)", resp.text)
        if body_match:
            return body_match.group(1)
        return None

    def _build_doc_range_ids(
        self,
        *,
        doc_range_start: int | None,
        doc_range_end: int | None,
    ) -> list[str]:
        if doc_range_start is None and doc_range_end is None:
            return []
        if doc_range_start is None or doc_range_end is None:
            raise ValueError("--doc-range-start and --doc-range-end must be provided together")
        if doc_range_start > doc_range_end:
            raise ValueError("--doc-range-start must be <= --doc-range-end")
        return [str(value) for value in range(doc_range_start, doc_range_end + 1)]

    def _ordered_deduplicate(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for value in values:
            item = str(value).strip()
            if not item or item in seen:
                continue
            seen.add(item)
            ordered.append(item)
        return ordered

    def _summarize(self, title: str, content: str, max_sentences: int) -> str:
        cleaned = self._cleanup_text(content)
        if not cleaned:
            return ""
        sentences = [value.strip() for value in _SENTENCE_SPLIT_PATTERN.split(cleaned) if value.strip()]
        if not sentences:
            return cleaned[:240]
        frequency = Counter(self._meaningful_tokens(cleaned))
        title_tokens = set(self._meaningful_tokens(title))
        scored: list[tuple[float, int, str]] = []
        for idx, sentence in enumerate(sentences):
            sentence_tokens = self._meaningful_tokens(sentence)
            if not sentence_tokens:
                continue
            overlap_score = sum(1 for token in sentence_tokens if token in title_tokens)
            tf_score = sum(frequency[token] for token in sentence_tokens)
            score = overlap_score * 2 + tf_score
            scored.append((float(score), idx, sentence))
        if not scored:
            return " ".join(sentences[:max_sentences])
        scored.sort(key=lambda item: (-item[0], item[1]))
        picked = scored[:max_sentences]
        picked.sort(key=lambda item: item[1])
        return " ".join(item[2] for item in picked)

    def _extract_keywords(self, title: str, content: str, top_k: int) -> list[str]:
        tokens = self._meaningful_tokens(f"{title}\n{content}")
        if not tokens:
            return []
        counts = Counter(tokens)
        first_seen: dict[str, int] = {}
        for idx, token in enumerate(tokens):
            first_seen.setdefault(token, idx)
        ranked = sorted(counts.keys(), key=lambda token: (-counts[token], first_seen[token], token))
        return ranked[:top_k]

    def _meaningful_tokens(self, text: str) -> list[str]:
        tokens = []
        for token in _TOKEN_PATTERN.findall(text.lower()):
            if token in _STOPWORDS:
                continue
            if token.isdigit():
                continue
            if len(token) == 1 and not self._is_cjk(token):
                continue
            tokens.append(token)
        return tokens

    def _cleanup_text(self, text: str) -> str:
        cleaned = text.replace("\r\n", "\n")
        cleaned = re.sub(r"`{1,3}.*?`{1,3}", " ", cleaned)
        cleaned = re.sub(r"[*_>#-]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _is_cjk(self, token: str) -> bool:
        return bool(re.fullmatch(r"[\u4e00-\u9fff]+", token))
