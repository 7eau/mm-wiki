from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent.mmwiki.state import DEFAULT_SERVER, load_profile, resolve_server, save_profile


class StateTests(unittest.TestCase):
    def test_resolve_server_precedence_and_fallback(self) -> None:
        with TemporaryDirectory() as tmpdir:
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmpdir) / "cfg")
            os.environ["XDG_DATA_HOME"] = str(Path(tmpdir) / "data")

            self.assertEqual(resolve_server("p", None), DEFAULT_SERVER)

            save_profile("p", "http://saved:8080/")
            self.assertEqual(resolve_server("p", None), "http://saved:8080")

            self.assertEqual(resolve_server("p", "http://cli:8080/"), "http://cli:8080")
            profile = load_profile("p")
            assert profile is not None
            self.assertEqual(profile.server, "http://cli:8080")


if __name__ == "__main__":
    unittest.main()
