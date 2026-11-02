"""地点接口必须同时兼容内存中的 Pydantic 结果和磁盘中的 dict 结果。"""

import sys
import unittest
from pathlib import Path
from unittest import mock

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api.routes import places  # noqa: E402
from app.api.routes import trip  # noqa: E402
from app.models.schemas import DayPlan, Location, TripPlan, TripPlanResponse  # noqa: E402
from app.services import place_store  # noqa: E402


def _response() -> TripPlanResponse:
    plan = TripPlan(
        city="西安",
        cities=["西安"],
        start_date="2026-11-10",
        end_date="2026-11-11",
        days=[
            DayPlan(
                date="2026-11-10",
                day_index=0,
                description="测试",
                transportation="步行",
                accommodation="经济型酒店",
                attractions=[],
                meals=[],
            )
        ],
        weather_info=[],
        overall_suggestions="测试",
    )
    return TripPlanResponse(success=True, message="ok", plan_id="pytest-plan", data=plan)


class PlacesTaskNormalizationTest(unittest.TestCase):
    def test_pydantic_result_is_converted_to_dict(self):
        task_id = "pytest-plan"
        trip._tasks[task_id] = {
            "task_id": task_id,
            "plan_id": task_id,
            "status": "completed",
            "result": _response(),
            "subscribers": [],
        }
        try:
            with mock.patch.object(place_store, "seed_from_plan", return_value=False):
                task = places._get_plan_task(task_id)
            self.assertIsInstance(task["result"], dict)
            self.assertIn("data", task["result"])
        finally:
            trip._tasks.pop(task_id, None)

    def test_place_store_accepts_pydantic_result(self):
        task = {
            "result": _response(),
        }
        data = place_store._plan_data(task)
        self.assertEqual(data.get("city"), "西安")
        self.assertEqual(len(data.get("days") or []), 1)


if __name__ == "__main__":
    unittest.main()
