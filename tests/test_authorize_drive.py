import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("authorize_drive", ROOT / "authorize_drive.py")
authorize_drive = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(authorize_drive)


class ResolveClientSecretPathTests(unittest.TestCase):
    def test_prefers_explicit_env_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            secret_path = Path(tmpdir) / "client_secret.json"
            secret_path.write_text("{}", encoding="utf-8")

            previous = os.environ.get("GDRIVE_CLIENT_SECRET")
            try:
                os.environ["GDRIVE_CLIENT_SECRET"] = str(secret_path)
                self.assertEqual(authorize_drive.resolve_client_secret_path(), str(secret_path))
            finally:
                if previous is None:
                    os.environ.pop("GDRIVE_CLIENT_SECRET", None)
                else:
                    os.environ["GDRIVE_CLIENT_SECRET"] = previous


if __name__ == "__main__":
    unittest.main()
