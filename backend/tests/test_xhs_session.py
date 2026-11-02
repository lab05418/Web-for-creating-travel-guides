"""小红书会话加密/状态机回归测试（离线，不调用平台）。"""

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.xhs.cookie_utils import normalize_xhs_cookie  # noqa: E402
from app.services.xhs.session_store import SessionStore  # noqa: E402


class XhsSessionStoreTest(unittest.TestCase):
    def test_cookie_is_encrypted_and_roundtrips(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SessionStore(root / "xhs.db", root / "xhs.key")
            cookie = "a1=test-a1; web_session=test-session; webId=test-id"
            store.import_cookie(cookie, account_label="unit")

            active = store.get_active(include_cookie=True)
            self.assertIsNotNone(active)
            self.assertEqual(active["cookie"], cookie)
            self.assertEqual(active["status"], "active")

            conn = sqlite3.connect(root / "xhs.db")
            cipher_text = conn.execute("SELECT cookie_cipher FROM xhs_sessions").fetchone()[0]
            conn.close()
            self.assertNotIn("test-session", cipher_text)

    def test_auth_failure_marks_expired(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SessionStore(root / "xhs.db", root / "xhs.key")
            session_id = store.import_cookie("a1=x; web_session=y")
            store.mark_failure(session_id, status="expired", note="300011")
            status = store.get_active(include_cookie=False)
            self.assertEqual(status["status"], "expired")
            self.assertEqual(status["fail_count"], 1)

    def test_cookie_json_normalizes_to_header_string(self):
        raw = '[{"name":"a1","value":"abc"},{"name":"web_session","value":"xyz"}]'
        self.assertEqual(normalize_xhs_cookie(raw), "a1=abc; web_session=xyz")


if __name__ == "__main__":
    unittest.main()
