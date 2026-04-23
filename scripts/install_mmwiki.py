#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import platform
import stat
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_bin_dir(bin_dir: str | None) -> Path:
    if bin_dir:
        return Path(bin_dir).expanduser().resolve()
    return Path.cwd().resolve()


def write_unix_launcher(path: Path, root: Path, module: str) -> None:
    launcher = f"""#!/usr/bin/env sh
ROOT="{root}"
if [ -n "$PYTHONPATH" ]; then
  export PYTHONPATH="$ROOT:$PYTHONPATH"
else
  export PYTHONPATH="$ROOT"
fi
if command -v python3 >/dev/null 2>&1; then
  exec python3 -m {module} "$@"
fi
exec python -m {module} "$@"
"""
    path.write_text(launcher, encoding="utf-8")
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def write_windows_launchers(bin_dir: Path, root: Path, name: str, module: str) -> list[Path]:
    cmd_path = bin_dir / f"{name}.cmd"
    cmd_content = f"""@echo off
set "ROOT={root}"
if defined PYTHONPATH (
  set "PYTHONPATH=%ROOT%;%PYTHONPATH%"
) else (
  set "PYTHONPATH=%ROOT%"
)
py -m {module} %*
"""
    cmd_path.write_text(cmd_content, encoding="utf-8")

    ps1_path = bin_dir / f"{name}.ps1"
    ps1_content = f"""$env:ROOT = "{root}"
if ($env:PYTHONPATH) {{
  $env:PYTHONPATH = "$env:ROOT;$env:PYTHONPATH"
}} else {{
  $env:PYTHONPATH = "$env:ROOT"
}}
py -m {module} @args
"""
    ps1_path.write_text(ps1_content, encoding="utf-8")
    return [cmd_path, ps1_path]


def print_path_hint(bin_dir: Path, *, is_default_local: bool) -> None:
    system = platform.system().lower()
    if is_default_local:
        print("\nInstalled in current directory; run directly:")
        if system == "windows":
            print("  .\\mmwiki.cmd --help")
        else:
            print("  ./mmwiki --help")
        return
    if system == "windows":
        print("\nAdd this directory to your PATH (User PATH):")
        print(f"  {bin_dir}")
        print("\nThen open a new terminal and run:")
        print("  mmwiki --help")
        return
    shell = os.environ.get("SHELL", "")
    profile = "~/.profile"
    if shell.endswith("zsh"):
        profile = "~/.zshrc"
    elif shell.endswith("bash"):
        profile = "~/.bashrc"
    print("\nIf not already in PATH, add this line:")
    print(f'  export PATH="{bin_dir}:$PATH"')
    print(f"to {profile}, then reload shell.")
    print("\nThen run:")
    print("  mmwiki --help")


def main() -> int:
    parser = argparse.ArgumentParser(description="Install mmwiki launcher for current user")
    parser.add_argument(
        "--bin-dir",
        default=None,
        help="Target directory for launcher script (default: current directory)",
    )
    args = parser.parse_args()

    if sys.version_info < (3, 9):
        print("Python 3.9+ is required.", file=sys.stderr)
        return 1

    root = repo_root()
    bin_dir = resolve_bin_dir(args.bin_dir)
    bin_dir.mkdir(parents=True, exist_ok=True)

    created: list[Path] = []
    if platform.system().lower() == "windows":
        created.extend(write_windows_launchers(bin_dir, root, "mmwiki", "agent.mmwiki.cli"))
        created.extend(write_windows_launchers(bin_dir, root, "mmwiki-preindex", "agent.mmwiki.preindex"))
    else:
        launcher = bin_dir / "mmwiki"
        write_unix_launcher(launcher, root, "agent.mmwiki.cli")
        created.append(launcher)
        preindex_launcher = bin_dir / "mmwiki-preindex"
        write_unix_launcher(preindex_launcher, root, "agent.mmwiki.preindex")
        created.append(preindex_launcher)

    print("Installed mmwiki launcher(s):")
    for item in created:
        print(f"  {item}")
    print_path_hint(bin_dir, is_default_local=args.bin_dir is None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
