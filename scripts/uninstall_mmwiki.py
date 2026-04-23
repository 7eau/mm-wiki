#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import platform
import shutil
from pathlib import Path


def resolve_bin_dir(bin_dir: str | None) -> Path:
    if bin_dir:
        return Path(bin_dir).expanduser().resolve()
    return Path.cwd().resolve()


def default_config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return Path(base) / "mmwiki"
    return Path.home() / ".config" / "mmwiki"


def default_data_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME")
    if base:
        return Path(base) / "mmwiki"
    return Path.home() / ".local" / "share" / "mmwiki"


def remove_file(path: Path) -> bool:
    if not path.exists():
        return False
    if path.is_file() or path.is_symlink():
        path.unlink()
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Uninstall mmwiki launcher for current user")
    parser.add_argument(
        "--bin-dir",
        default=None,
        help="Launcher directory to clean (default: current directory)",
    )
    parser.add_argument(
        "--purge-state",
        action="store_true",
        help="Also remove local mmwiki config/data (profiles, cookies, cache, index)",
    )
    args = parser.parse_args()

    system = platform.system().lower()
    bin_dir = resolve_bin_dir(args.bin_dir)

    removed = []
    kept = []

    if system == "windows":
        targets = [
            bin_dir / "mmwiki.cmd",
            bin_dir / "mmwiki.ps1",
            bin_dir / "mmwiki-preindex.cmd",
            bin_dir / "mmwiki-preindex.ps1",
        ]
    else:
        targets = [bin_dir / "mmwiki", bin_dir / "mmwiki-preindex"]

    for target in targets:
        if remove_file(target):
            removed.append(target)
        else:
            kept.append(target)

    print("Uninstall results:")
    if removed:
        print("Removed launcher(s):")
        for item in removed:
            print(f"  {item}")
    else:
        print("No launcher files found to remove.")

    if args.purge_state:
        cfg = default_config_dir()
        data = default_data_dir()
        for folder in (cfg, data):
            if folder.exists():
                shutil.rmtree(folder)
                print(f"Removed state dir: {folder}")
            else:
                print(f"State dir not found: {folder}")
    else:
        print("Kept local state (use --purge-state to remove it).")

    print("\nIf you manually added PATH entries for mmwiki, you can now remove them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
