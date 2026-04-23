from __future__ import annotations

import os
from pathlib import Path


APP_NAME = "mmwiki"


def _xdg_path(env_key: str, default_suffix: str) -> Path:
    base = os.environ.get(env_key)
    if base:
        return Path(base) / APP_NAME
    return Path.home() / default_suffix / APP_NAME


def config_dir() -> Path:
    return _xdg_path("XDG_CONFIG_HOME", ".config")


def data_dir() -> Path:
    return _xdg_path("XDG_DATA_HOME", ".local/share")


def ensure_dirs() -> None:
    for path in (
        config_dir(),
        data_dir(),
        data_dir() / "cookies",
        data_dir() / "cache",
        data_dir() / "index",
    ):
        path.mkdir(parents=True, exist_ok=True)

