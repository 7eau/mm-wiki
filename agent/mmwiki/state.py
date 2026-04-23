from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .paths import config_dir, data_dir, ensure_dirs


@dataclass(frozen=True)
class Profile:
    name: str
    server: str


def _profiles_file() -> Path:
    ensure_dirs()
    return config_dir() / "profiles.json"


def _snapshots_file() -> Path:
    ensure_dirs()
    return data_dir() / "cache" / "snapshots.json"


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def save_profile(name: str, server: str) -> None:
    profiles = _load_json(_profiles_file(), {})
    profiles[name] = {"server": server.rstrip("/")}
    _save_json(_profiles_file(), profiles)


def load_profile(name: str) -> Profile | None:
    profiles = _load_json(_profiles_file(), {})
    value = profiles.get(name)
    if not value:
        return None
    return Profile(name=name, server=value["server"])


def resolve_server(profile_name: str, server: str | None) -> str:
    if server:
        save_profile(profile_name, server)
        return server.rstrip("/")
    profile = load_profile(profile_name)
    if profile:
        return profile.server
    raise ValueError(f"profile '{profile_name}' has no configured server; pass --server first")


def snapshot_key(server: str, profile: str, document_id: str, md_path: str) -> str:
    return f"{server}|{profile}|{document_id}|{md_path}"


def get_snapshot(server: str, profile: str, document_id: str, md_path: str) -> dict[str, Any] | None:
    snapshots = _load_json(_snapshots_file(), {})
    return snapshots.get(snapshot_key(server, profile, document_id, md_path))


def set_snapshot(
    server: str,
    profile: str,
    document_id: str,
    md_path: str,
    sha256: str,
    title: str,
) -> None:
    snapshots = _load_json(_snapshots_file(), {})
    snapshots[snapshot_key(server, profile, document_id, md_path)] = {
        "sha256": sha256,
        "title": title,
    }
    _save_json(_snapshots_file(), snapshots)

