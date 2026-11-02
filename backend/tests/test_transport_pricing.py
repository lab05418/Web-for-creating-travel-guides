"""12306 里程计价与席别系数回归测试（离线，不调用地图服务）。"""

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
    Location,
    Meal,
    TripPlan,
    TripRequest,
)
from app.services.budget_service import normalize_budget  # noqa: E402
from app.services.transport_pricing import (  # noqa: E402
    MODE_MIN_FARES,
    MODE_RATES,
    SEAT_MULTIPLIERS_BY_MODE,
    build_city_sequence,
    calculate_quote,
    calculate_ticket_price,
    distance_fare,
    normalize_seat_type,
)

COORDS = {
    "上海": (121.4737, 31.2304),
    "西安": (108.9398, 34.3416),
    "成都": (104.0665, 30.5728),
}


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
        "intercity_transportation": "高铁",
        "intercity_seat_type": "二等座",
    }
    payload.update(overrides)
    return TripRequest(**payload)


def _plan() -> TripPlan:
    return TripPlan(
        city="西安",
        cities=["西安"],
        start_date="2026-11-10",
        end_date="2026-11-11",
        days=[
            DayPlan(
                date="2026-11-10",
                day_index=0,
                city="西安",
                description="第一天",
                transportation="公共交通",
                accommodation="经济型酒店",
                attractions=[
                    Attraction(
                        name="测试景点",
                        address="西安",
                        location=Location(longitude=108.94, latitude=34.34),
                        visit_duration=120,
                        description="测试",
                        ticket_price=60,
                    )
                ],
                meals=[Meal(type="lunch", name="午餐", estimated_cost=50)],
            )
        ],
        weather_info=[],
        overall_suggestions="测试",
        budget=Budget(total_inter_city_transport=999, total=999),
    )


class TransportPricingTest(unittest.TestCase):
    def test_seat_types_use_fixed_multipliers(self):
        second = calculate_ticket_price(1000, "高铁", "二等座")
        first = calculate_ticket_price(1000, "高铁", "一等座")
        business = calculate_ticket_price(1000, "高铁", "商务座")

        self.assertEqual(second, round(max(MODE_MIN_FARES["高铁"], distance_fare(1000, "高铁"))))
        self.assertEqual(first, round(second * SEAT_MULTIPLIERS_BY_MODE["高铁"]["一等座"]))
        self.assertEqual(business, round(second * SEAT_MULTIPLIERS_BY_MODE["高铁"]["商务座"]))
        self.assertEqual(normalize_seat_type("高铁", "不存在的席别"), "二等座")

    def test_each_mode_has_independent_seat_categories(self):
        # 高铁：二等/一等/特等/商务/无座
        self.assertEqual(normalize_seat_type("高铁", "商务座"), "商务座")
        self.assertEqual(normalize_seat_type("高铁", "无座"), "无座")
        self.assertEqual(normalize_seat_type("高铁", "硬卧"), "二等座")
        # 火车：硬座/软座/硬卧/软卧/高级软卧/无座
        self.assertEqual(normalize_seat_type("火车", "硬卧"), "硬卧")
        self.assertEqual(normalize_seat_type("火车", "商务座"), "硬座")
        # 飞机：经济/超级经济/公务/头等
        self.assertEqual(normalize_seat_type("飞机", "公务舱"), "公务舱")
        self.assertEqual(normalize_seat_type("飞机", "一等座"), "经济舱")
        self.assertIsNone(normalize_seat_type("自驾", "二等座"))

        train_sleeper = calculate_ticket_price(1000, "火车", "硬卧")
        train_hard = calculate_ticket_price(1000, "火车", "硬座")
        flight_business = calculate_ticket_price(1000, "飞机", "公务舱")
        flight_economy = calculate_ticket_price(1000, "飞机", "经济舱")
        self.assertGreater(train_sleeper, train_hard)
        self.assertGreater(flight_business, flight_economy)

    def test_three_modes_share_same_distance_ladder(self):
        defaults = {"高铁": "二等座", "火车": "硬座", "飞机": "经济舱"}
        for mode, seat in defaults.items():
            expected_base = int(round(max(MODE_MIN_FARES[mode], distance_fare(1000, mode))))
            self.assertEqual(calculate_ticket_price(1000, mode, seat), expected_base)

    def test_longer_distance_has_lower_marginal_rate(self):
        short_rate = distance_fare(200, "高铁") / 200
        long_rate = distance_fare(2000, "高铁") / 2000
        self.assertGreater(short_rate, long_rate)

    def test_round_trip_and_multi_city_legs(self):
        self.assertEqual(build_city_sequence("上海", ["西安", "成都"]), ["上海", "西安", "成都", "上海"])
        self.assertEqual(build_city_sequence("", ["西安", "成都"]), ["西安", "成都", "西安"])

        quote = calculate_quote("上海", ["西安", "成都"], "高铁", "二等座", COORDS)
        self.assertIsNotNone(quote)
        self.assertEqual(len(quote.legs), 3)
        self.assertEqual(quote.ticket_total, sum(leg.fare for leg in quote.legs))
        self.assertGreater(quote.distance_km, 0)

        no_origin_quote = calculate_quote("", ["西安", "成都"], "高铁", "二等座", COORDS)
        self.assertIsNotNone(no_origin_quote)
        self.assertEqual(len(no_origin_quote.legs), 2)
        self.assertEqual(no_origin_quote.legs[0].distance_km, no_origin_quote.legs[1].distance_km)
        self.assertEqual(no_origin_quote.ticket_total, no_origin_quote.legs[0].fare * 2)

    def test_quote_returns_none_when_coordinates_missing(self):
        quote = calculate_quote("上海", ["西安"], "高铁", "二等座", {"上海": COORDS["上海"]})
        self.assertIsNone(quote)
        self.assertIsNone(calculate_ticket_price(100, "自驾", "二等座"))

    def test_single_city_without_origin_is_zero(self):
        quote = calculate_quote("", ["西安"], "高铁", "二等座", COORDS)
        self.assertIsNotNone(quote)
        self.assertEqual(quote.ticket_total, 0)

    def test_normalize_budget_uses_quote_and_keeps_metadata(self):
        quote = calculate_quote("上海", ["西安"], "高铁", "一等座", COORDS)
        budget = normalize_budget(_plan(), _request(intercity_seat_type="一等座"), quote)

        self.assertEqual(budget.total_inter_city_transport, quote.ticket_total)
        self.assertEqual(budget.intercity_transport_mode, "高铁")
        self.assertEqual(budget.intercity_seat_type, "一等座")
        self.assertEqual(budget.intercity_pricing_basis, "12306_distance_rule")
        self.assertEqual(budget.intercity_distance_km, quote.distance_km)

    def test_quote_enters_total_only_when_switch_is_on(self):
        quote = calculate_quote("上海", ["西安"], "高铁", "二等座", COORDS)
        excluded = normalize_budget(_plan(), _request(), quote)
        included = normalize_budget(
            _plan(),
            _request(include_inter_city_transport_in_budget=True),
            quote,
        )

        self.assertEqual(included.total_inter_city_transport, quote.ticket_total)
        self.assertEqual(included.total - excluded.total, quote.ticket_total)

    def test_train_quote_keeps_train_seat_metadata(self):
        quote = calculate_quote("上海", ["西安"], "火车", "硬卧", COORDS)
        budget = normalize_budget(
            _plan(),
            _request(intercity_transportation="火车", intercity_seat_type="硬卧"),
            quote,
        )

        self.assertEqual(budget.intercity_transport_mode, "火车")
        self.assertEqual(budget.intercity_seat_type, "硬卧")
        self.assertEqual(budget.total_inter_city_transport, quote.ticket_total)

    def test_request_normalizes_seat_to_current_mode(self):
        train_request = _request(intercity_transportation="火车", intercity_seat_type="商务座")
        flight_request = _request(intercity_transportation="飞机", intercity_seat_type="商务座")
        drive_request = _request(intercity_transportation="自驾", intercity_seat_type="商务座")

        self.assertEqual(train_request.intercity_seat_type, "硬座")
        self.assertEqual(flight_request.intercity_seat_type, "经济舱")
        self.assertIsNone(drive_request.intercity_seat_type)

    def test_unsupported_mode_keeps_llm_estimate(self):
        budget = normalize_budget(
            _plan(),
            _request(intercity_transportation="自驾", intercity_seat_type="商务座"),
        )
        self.assertEqual(budget.total_inter_city_transport, 999)
        self.assertIsNone(budget.intercity_seat_type)
        self.assertEqual(budget.intercity_pricing_basis, "llm_estimate")


if __name__ == "__main__":
    unittest.main()
