"""小红书签名运行时回归测试：必须选择 Node，不能回退 JScript。"""

import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.xhs_sign.sign_util import _RUNTIME  # noqa: E402


class XhsSignRuntimeTest(unittest.TestCase):
    def test_node_runtime_is_selected(self):
        self.assertIn("Node", _RUNTIME.name)
        self.assertNotIn("JScript", _RUNTIME.name)

    def test_trace_id_can_be_generated(self):
        from app.services.xhs_sign.sign_util import generate_x_b3_traceid, generate_xray_traceid

        self.assertEqual(len(generate_x_b3_traceid(16)), 16)
        self.assertTrue(generate_xray_traceid())


if __name__ == "__main__":
    unittest.main()
