"""预算归一化规则回归测试（离线，不调用 LLM/地图服务）。"""

import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models.schemas import (  # noqa: E402
    Attraction,
    Budget,
    DayPlan,
    Hotel,
    Location,
    Meal,
    TripPlan,
    TripRequest,
)
from app.services.budget_service import normalize_budget  # noqa: E402


def _request(**overrides) -> TripRequest:
    payload = {
        "origin": "上海",
        "city": "西安",
        "cities": [{"city": "西安", "days": 2}],
        "start_date": "2026-11-10",
        "end_date": "2026-11-11",
        "travel_days": 2,
        "transportation": "公共交通",
        "accommodation": "经济型酒店",
    }
    payload.update(overrides)
    return TripRequest(**payload)


def _plan() -> TripPlan:
    day = DayPlan(
        date="2026-11-10",
        day_index=0,
        description="第一天",
        transportation="公共交通",
        accommodation="经济型酒店",
        hotel=Hotel(name="测试酒店", estimated_cost=400),
        attractions=[
            Attraction(
                name="测试景点",
                address="西安",
                location=Location(longitude=108.9, latitude=34.2),
                visit_duration=120,
                description="测试",
                ticket_price=60,
            )
        ],
        meals=[
            Meal(type="breakfast", name="早餐", estimated_cost=30),
            Meal(type="lunch", name="午餐", estimated_cost=50),
            Meal(type="dinner", name="晚餐", estimated_cost=80),
        ],
    )
    return TripPlan(
        city="西安",
        cities=["西安"],
        start_date="2026-11-10",
        end_date="2026-11-11",
        days=[day],
        weather_info=[],
        overall_suggestions="测试计划",
        budget=Budget(
            total_attractions=999,
            total_hotels=999,
            total_meals=999,
            total_transportation=100,
            total_inter_city_transport=500,
            total=99999,
        ),
    )


class BudgetPolicyTest(unittest.TestCase):
    def test_default_excludes_intercity_from_total(self):
        plan = _plan()
        budget = normalize_budget(plan, _request())

        self.assertEqual(budget.total_attractions, 60)
        self.assertEqual(budget.total_hotels, 400)
        self.assertEqual(budget.total_meals, 160)
        self.assertEqual(budget.total_transportation, 100)
        self.assertEqual(budget.total_inter_city_transport, 500)
        self.assertEqual(budget.total, 720)
        self.assertFalse(budget.include_inter_city_transport_in_budget)
        self.assertIsNone(budget.budget_limit)

    def test_include_intercity_adds_it_to_total(self):
        plan = _plan()
        budget = normalize_budget(
            plan,
            _request(
                include_inter_city_transport_in_budget=True,
                budget_amount=5000,
            ),
        )

        self.assertEqual(budget.total, 1220)
        self.assertTrue(budget.include_inter_city_transport_in_budget)
        self.assertEqual(budget.budget_limit, 5000)

    def test_single_city_without_origin_forces_intercity_zero(self):
        plan = _plan()
        budget = normalize_budget(
            plan,
            _request(
                origin="",
                cities=[{"city": "西安", "days": 2}],
                city="西安",
            ),
        )

        self.assertEqual(budget.total_inter_city_transport, 0)
        self.assertEqual(budget.total, 720)

    def test_multi_city_without_origin_keeps_intercity(self):
        plan = _plan()
        budget = normalize_budget(
            plan,
            _request(
                origin="",
                cities=[{"city": "西安", "days": 1}, {"city": "成都", "days": 1}],
                city="西安",
            ),
        )

        self.assertEqual(budget.total_inter_city_transport, 500)

    def test_llm_category_totals_are_replaced_by_detail_sums(self):
        plan = _plan()
        budget = normalize_budget(plan, _request())

        self.assertNotEqual(budget.total_attractions, 999)
        self.assertNotEqual(budget.total_hotels, 999)
        self.assertNotEqual(budget.total_meals, 999)


if __name__ == "__main__":
    unittest.main()
