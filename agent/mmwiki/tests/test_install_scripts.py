from __future__ import annotations

import importlib.util
import io
import os
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InstallScriptsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).resolve().parents[3]
        cls.install_script = _load_module(root / "scripts" / "install_mmwiki.py", "install_mmwiki_script")
        cls.uninstall_script = _load_module(root / "scripts" / "uninstall_mmwiki.py", "uninstall_mmwiki_script")

    def test_resolve_bin_dir_defaults_to_cwd(self) -> None:
        with TemporaryDirectory() as tmpdir:
            previous = Path.cwd()
            os.chdir(tmpdir)
            try:
                expected = Path(tmpdir).resolve()
                self.assertEqual(self.install_script.resolve_bin_dir(None), expected)
                self.assertEqual(self.uninstall_script.resolve_bin_dir(None), expected)
            finally:
                os.chdir(previous)

    def test_resolve_bin_dir_honors_explicit_path(self) -> None:
        with TemporaryDirectory() as tmpdir:
            previous = Path.cwd()
            os.chdir(tmpdir)
            try:
                expected = (Path(tmpdir) / "custom-bin").resolve()
                self.assertEqual(self.install_script.resolve_bin_dir("custom-bin"), expected)
                self.assertEqual(self.uninstall_script.resolve_bin_dir("custom-bin"), expected)
            finally:
                os.chdir(previous)

    def test_install_prints_local_run_hint_for_default_mode(self) -> None:
        out = io.StringIO()
        with patch.object(self.install_script.platform, "system", return_value="Linux"):
            with redirect_stdout(out):
                self.install_script.print_path_hint(Path("/tmp/example"), is_default_local=True)
        output = out.getvalue()
        self.assertIn("./mmwiki --help", output)
        self.assertNotIn("export PATH=", output)

    def test_uninstall_defaults_to_current_dir(self) -> None:
        with TemporaryDirectory() as tmpdir:
            previous = Path.cwd()
            os.chdir(tmpdir)
            try:
                (Path(tmpdir) / "mmwiki").write_text("x", encoding="utf-8")
                (Path(tmpdir) / "mmwiki-preindex").write_text("x", encoding="utf-8")
                with patch("sys.argv", ["uninstall_mmwiki.py"]):
                    code = self.uninstall_script.main()
                self.assertEqual(code, 0)
                self.assertFalse((Path(tmpdir) / "mmwiki").exists())
                self.assertFalse((Path(tmpdir) / "mmwiki-preindex").exists())
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
