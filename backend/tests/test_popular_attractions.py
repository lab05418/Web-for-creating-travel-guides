"""热门景点解析/过滤回归测试（离线，不调用高德）。"""

import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.popular_attractions import (  # noqa: E402
    _dedupe_and_sort,
    _is_excluded,
    _to_item,
)


class PopularAttractionsTest(unittest.TestCase):
    def test_attraction_poi_becomes_item(self):
        poi = {
            "id": "B0FFTEST",
            "name": "中山陵景区",
            "type": "风景名胜;风景名胜;国家级景点",
            "address": "石象路7号",
            "location": "118.853,32.059",
            "biz_ext": {"rating": "4.9", "cost": []},
            "photos": [{"url": "https://example.com/a.jpg"}],
        }
        item = _to_item(poi, "南京")
        self.assertIsNotNone(item)
        self.assertEqual(item["name"], "中山陵景区")
        self.assertEqual(item["category"], "国家级景点")
        self.assertEqual(item["location"], {"longitude": 118.853, "latitude": 32.059})
        self.assertEqual(item["photos"], ["https://example.com/a.jpg"])
        self.assertEqual(item["rating"], 4.9)

    def test_hotel_or_invalid_location_is_rejected(self):
        hotel = {
            "name": "某酒店",
            "type": "住宿服务;宾馆酒店",
            "location": "118.8,32.0",
        }
        no_location = {
            "name": "某景点",
            "type": "风景名胜;风景名胜",
            "location": [],
        }
        self.assertIsNone(_to_item(hotel, "南京"))
        self.assertIsNone(_to_item(no_location, "南京"))

    def test_exclusion_handles_common_suffixes(self):
        excluded = {"玄武湖", "鸡鸣寺", "南京博物院"}
        self.assertTrue(_is_excluded("玄武湖景区", excluded))
        self.assertTrue(_is_excluded("古鸡鸣寺", excluded))
        self.assertTrue(_is_excluded("南京博物院", excluded))
        self.assertFalse(_is_excluded("中山陵景区", excluded))

    def test_dedupe_and_sort_prefers_rating_and_image(self):
        items = [
            {"name": "玄武湖景区", "rating": 4.8, "image_url": "a"},
            {"name": "玄武湖", "rating": 4.7, "image_url": ""},
            {"name": "中山陵景区", "rating": 4.9, "image_url": "b"},
            {"name": "低分景点", "rating": 4.2, "image_url": ""},
        ]
        result = _dedupe_and_sort(items, 10)
        self.assertEqual([item["name"] for item in result], ["中山陵景区", "玄武湖景区", "低分景点"])


if __name__ == "__main__":
    unittest.main()
