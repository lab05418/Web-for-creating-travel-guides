"""地点价格解析、类型推断与预算重算测试（不访问网络）。"""

import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.place_price import _infer_type, _parse_money  # noqa: E402
from app.services.place_store import _refresh_plan_budget  # noqa: E402


class PlacePriceTest(unittest.TestCase):
    def test_parse_money_variants(self):
        self.assertEqual(_parse_money("70.00"), 70.0)
        self.assertEqual(_parse_money(["88"]), 88.0)
        self.assertEqual(_parse_money({"cost": "120元"}), 120.0)
        self.assertIsNone(_parse_money([]))
        self.assertIsNone(_parse_money("暂无"))

    def test_infer_type_from_poi_content(self):
        self.assertEqual(_infer_type("餐饮服务;中餐厅;江苏菜", "custom"), "restaurant")
        self.assertEqual(_infer_type("住宿服务;宾馆酒店;经济型", "custom"), "hotel")
        self.assertEqual(_infer_type("风景名胜;博物馆", "custom"), "attraction")
        self.assertEqual(_infer_type("交通设施服务;地铁站", "custom"), "station")
        self.assertEqual(_infer_type("未知", "custom"), "custom")

    def test_budget_refresh_includes_only_available_costs(self):
        plan = {
            "budget": {
                "total_transportation": 60,
                "total_inter_city_transport": 120,
                "include_inter_city_transport_in_budget": False,
                "budget_limit": 3000,
            },
            "days": [
                {
                    "attractions": [{"ticket_price": 0}, {"ticket_price": 45}],
                    "hotel": {"estimated_cost": 350},
                    "meals": [{"estimated_cost": 70}, {"estimated_cost": 0}],
                }
            ],
        }
        _refresh_plan_budget(plan)
        budget = plan["budget"]
        self.assertEqual(budget["total_attractions"], 45)
        self.assertEqual(budget["total_hotels"], 350)
        self.assertEqual(budget["total_meals"], 70)
        self.assertEqual(budget["total"], 525)
        self.assertEqual(budget["budget_limit"], 3000)


if __name__ == "__main__":
    unittest.main()
