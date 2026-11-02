"""地点持久化：SQLite 存储 + 从既有行程 JSON 首次迁移。

P0 范围：列表、新增、修改、删除、排序、设置酒店。
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "farway.db"

VALID_TYPES = {"hotel", "attraction", "restaurant", "station", "custom"}


def _pick_meal_type(name: str, note: str, day: Dict[str, Any]) -> str:
    """根据名称/备注和已有餐次，为新增餐饮选一个合理的餐次。"""
    text = f"{name} {note}"
    if any(word in text for word in ("早餐", "早饭")):
        return "breakfast"
    if any(word in text for word in ("午餐", "午饭", "中餐")):
        return "lunch"
    if any(word in text for word in ("晚餐", "晚饭", "夜市", "夜宵")):
        return "snack" if "夜宵" in text else "dinner"
    existing = {str(item.get("type") or "") for item in (day.get("meals") or [])}
    for meal_type in ("lunch", "dinner", "breakfast", "snack"):
        if meal_type not in existing:
            return meal_type
    return "snack"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS places (
  id TEXT PRIMARY KEY,
  plan_id TEXT NOT NULL,
  day_index INTEGER,
  type TEXT NOT NULL CHECK (type IN ('hotel','attraction','restaurant','station','custom')),
  name TEXT NOT NULL,
  address TEXT NOT NULL DEFAULT '',
  longitude REAL NOT NULL,
  latitude REAL NOT NULL,
  coord_system TEXT NOT NULL DEFAULT 'GCJ-02',
  source TEXT NOT NULL DEFAULT 'user',
  amap_poi_id TEXT,
  price REAL,
  price_source TEXT NOT NULL DEFAULT '',
  inferred_type TEXT NOT NULL DEFAULT '',
  note TEXT NOT NULL DEFAULT '',
  visit_duration_min INTEGER,
  order_index INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_places_plan_day ON places(plan_id, day_index, order_index);
CREATE UNIQUE INDEX IF NOT EXISTS uq_places_poi ON places(plan_id, amap_poi_id)
  WHERE amap_poi_id IS NOT NULL AND amap_poi_id <> '';
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    # 兼容已有 farway.db：CREATE TABLE IF NOT EXISTS 不会补列。
    columns = {row[1] for row in conn.execute("PRAGMA table_info(places)").fetchall()}
    for name, declaration in (
        ("price", "REAL"),
        ("price_source", "TEXT NOT NULL DEFAULT ''"),
        ("inferred_type", "TEXT NOT NULL DEFAULT ''"),
    ):
        if name not in columns:
            conn.execute(f"ALTER TABLE places ADD COLUMN {name} {declaration}")
    conn.commit()
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"pl_{uuid.uuid4().hex[:16]}"


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "plan_id": row["plan_id"],
        "day_index": row["day_index"],
        "type": row["type"],
        "name": row["name"],
        "address": row["address"],
        "location": {"longitude": row["longitude"], "latitude": row["latitude"]},
        "coord_system": row["coord_system"],
        "source": row["source"],
        "amap_poi_id": row["amap_poi_id"],
        "price": row["price"],
        "price_source": row["price_source"] or "",
        "inferred_type": row["inferred_type"] or "",
        "note": row["note"],
        "visit_duration_min": row["visit_duration_min"],
        "order_index": row["order_index"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "version": row["version"],
    }


def list_places(plan_id: str) -> List[Dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM places WHERE plan_id = ? "
            "ORDER BY COALESCE(day_index, 9999), order_index, created_at",
            (plan_id,),
        ).fetchall()
        return [_row_to_dict(row) for row in rows]
    finally:
        conn.close()


def count_places(plan_id: str) -> int:
    conn = _connect()
    try:
        row = conn.execute("SELECT COUNT(*) AS n FROM places WHERE plan_id = ?", (plan_id,)).fetchone()
        return int(row["n"]) if row else 0
    finally:
        conn.close()


def _plan_data(task: Dict[str, Any]) -> Dict[str, Any]:
    result = task.get("result") or {}
    if hasattr(result, "model_dump"):
        result = result.model_dump(mode="json")
    if not isinstance(result, dict):
        return {}
    return result.get("data") or {}


def _to_amount(value: Any) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0
    return max(0, int(round(number)))


def _refresh_plan_budget(plan: Dict[str, Any]) -> None:
    """地点增删改后同步行程预算，避免 status/导出读到旧总额。"""
    existing = plan.get("budget")
    if not isinstance(existing, dict):
        existing = {}
    attractions = 0
    hotels = 0
    meals = 0
    for day in plan.get("days") or []:
        if not isinstance(day, dict):
            continue
        for attraction in day.get("attractions") or []:
            attractions += _to_amount((attraction or {}).get("ticket_price"))
        if isinstance(day.get("hotel"), dict):
            hotels += _to_amount(day["hotel"].get("estimated_cost"))
        for meal in day.get("meals") or []:
            meals += _to_amount((meal or {}).get("estimated_cost"))

    local_transport = _to_amount(existing.get("total_transportation"))
    intercity = _to_amount(existing.get("total_inter_city_transport"))
    include_intercity = existing.get("include_inter_city_transport_in_budget") is not False
    total = attractions + hotels + meals + local_transport + (intercity if include_intercity else 0)
    plan["budget"] = {
        **existing,
        "total_attractions": attractions,
        "total_hotels": hotels,
        "total_meals": meals,
        "total_transportation": local_transport,
        "total_inter_city_transport": intercity,
        "include_inter_city_transport_in_budget": include_intercity,
        "budget_limit": existing.get("budget_limit"),
        "total": total,
    }


def _valid_location(value: Any) -> Optional[Dict[str, float]]:
    if not isinstance(value, dict):
        return None
    try:
        lng = float(value.get("longitude"))
        lat = float(value.get("latitude"))
    except (TypeError, ValueError):
        return None
    if not (-180 <= lng <= 180 and -90 <= lat <= 90):
        return None
    return {"longitude": lng, "latitude": lat}


def _insert(
    conn: sqlite3.Connection,
    *,
    plan_id: str,
    day_index: Optional[int],
    place_type: str,
    name: str,
    address: str,
    longitude: float,
    latitude: float,
    source: str,
    note: str,
    visit_duration_min: Optional[int],
    order_index: int,
    amap_poi_id: Optional[str],
    price: Optional[float] = None,
    price_source: str = "",
    inferred_type: str = "",
    place_id: Optional[str] = None,
) -> str:
    pid = place_id or _new_id()
    now = _now()
    conn.execute(
        "INSERT INTO places (id, plan_id, day_index, type, name, address, longitude, latitude,"
        " coord_system, source, amap_poi_id, price, price_source, inferred_type, note,"
        " visit_duration_min, order_index, created_at, updated_at, version)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'GCJ-02', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
        (
            pid, plan_id, day_index, place_type, name, address, longitude, latitude,
            source, amap_poi_id, price, price_source, inferred_type, note,
            visit_duration_min, order_index, now, now,
        ),
    )
    return pid


def seed_from_plan(plan_id: str, task: Dict[str, Any]) -> bool:
    """首次访问时，把行程中的景点/酒店迁移为 Place，并把 place_id 写回行程。"""
    if count_places(plan_id) > 0:
        return False
    plan = _plan_data(task)
    days = plan.get("days") or []
    if not days:
        return False

    conn = _connect()
    changed = False
    try:
        with conn:
            for day_index, day in enumerate(days):
                if not isinstance(day, dict):
                    continue
                for attr_index, attraction in enumerate(day.get("attractions") or []):
                    if not isinstance(attraction, dict):
                        continue
                    location = _valid_location(attraction.get("location"))
                    if not location:
                        continue
                    name = str(attraction.get("name") or "").strip()
                    if not name:
                        continue
                    pid = str(attraction.get("place_id") or _new_id())
                    attraction["place_id"] = pid
                    _insert(
                        conn,
                        plan_id=plan_id,
                        day_index=day_index,
                        place_type="attraction",
                        name=name,
                        address=str(attraction.get("address") or ""),
                        longitude=location["longitude"],
                        latitude=location["latitude"],
                        source="ai",
                        note=str(attraction.get("description") or ""),
                        visit_duration_min=attraction.get("visit_duration"),
                        order_index=attr_index,
                        amap_poi_id=str(attraction.get("poi_id") or "") or None,
                        price=float(attraction.get("ticket_price") or 0) or None,
                        price_source="plan",
                        inferred_type="attraction",
                        place_id=pid,
                    )
                    changed = True
                hotel = day.get("hotel")
                if isinstance(hotel, dict):
                    location = _valid_location(hotel.get("location"))
                    name = str(hotel.get("name") or "").strip()
                    if location and name:
                        pid = str(hotel.get("place_id") or _new_id())
                        hotel["place_id"] = pid
                        _insert(
                            conn,
                            plan_id=plan_id,
                            day_index=day_index,
                            place_type="hotel",
                            name=name,
                            address=str(hotel.get("address") or ""),
                            longitude=location["longitude"],
                            latitude=location["latitude"],
                            source="ai",
                            note=str(hotel.get("distance") or ""),
                            visit_duration_min=None,
                            order_index=0,
                            amap_poi_id=None,
                            price=float(hotel.get("estimated_cost") or 0) or None,
                            price_source="plan",
                            inferred_type="hotel",
                            place_id=pid,
                        )
                        changed = True
    finally:
        conn.close()
    return changed


def get_place(plan_id: str, place_id: str) -> Optional[Dict[str, Any]]:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM places WHERE plan_id = ? AND id = ?", (plan_id, place_id)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def create_place(plan_id: str, data: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
    plan = _plan_data(task)
    days = plan.get("days") or []
    day_index = data.get("day_index")
    if day_index is not None and not (0 <= int(day_index) < len(days)):
        raise ValueError("day_index 不存在")
    if day_index is not None:
        day_index = int(day_index)

    place_type = str(data.get("type") or "custom")
    if place_type not in VALID_TYPES:
        raise ValueError("地点类型不合法")
    location = _valid_location(data.get("location"))
    if not location:
        raise ValueError("经纬度不合法")
    name = str(data.get("name") or "").strip()
    if not name:
        raise ValueError("地点名称不能为空")

    raw_price = data.get("price")
    try:
        price = float(raw_price) if raw_price is not None else None
    except (TypeError, ValueError):
        price = None
    if price is not None and price < 0:
        price = None
    price_source = str(data.get("price_source") or "")
    inferred_type = str(data.get("inferred_type") or place_type)

    day = days[day_index] if day_index is not None else None
    if place_type == "hotel" and day is None:
        raise ValueError("酒店必须指定所属天")
    if place_type == "hotel" and day is not None and isinstance(day.get("hotel"), dict):
        # 每天一个酒店，先把旧酒店从 places 和行程中移除
        old_pid = day["hotel"].get("place_id")
        conn = _connect()
        try:
            with conn:
                if old_pid:
                    conn.execute("DELETE FROM places WHERE plan_id = ? AND id = ?", (plan_id, old_pid))
        finally:
            conn.close()

    conn = _connect()
    try:
        try:
            with conn:
                if place_type == "hotel" and day is not None:
                    order_index = 0
                elif place_type == "restaurant" and day is not None:
                    order_index = len(day.get("meals") or [])
                else:
                    order_index = len(day.get("attractions") or []) if day is not None else 0
                pid = _insert(
                    conn,
                    plan_id=plan_id,
                    day_index=day_index,
                    place_type=place_type,
                    name=name,
                    address=str(data.get("address") or ""),
                    longitude=location["longitude"],
                    latitude=location["latitude"],
                    source=str(data.get("source") or "user"),
                    note=str(data.get("note") or ""),
                    visit_duration_min=data.get("visit_duration_min"),
                    order_index=order_index,
                    amap_poi_id=str(data.get("amap_poi_id") or "") or None,
                    price=price,
                    price_source=price_source,
                    inferred_type=inferred_type,
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("该地点已存在，请勿重复添加") from exc
    finally:
        conn.close()

    adjusted = False
    adjustment_message = ""
    if day is not None:
        if place_type == "hotel":
            day["hotel"] = {
                "place_id": pid,
                "name": name,
                "address": str(data.get("address") or ""),
                "location": location,
                "price_range": f"约 ¥{int(price)}" if price else "",
                "rating": "",
                "distance": "",
                "type": "用户添加",
                "estimated_cost": int(round(price)) if price else 0,
            }
            adjusted = True
            adjustment_message = "已识别为住宿，并写入当日酒店预算" if price else "已识别为住宿；未查到价格，未计入预算"
        elif place_type == "restaurant":
            meal_type = _pick_meal_type(name, str(data.get("note") or ""), day)
            day.setdefault("meals", []).append(
                {
                    "place_id": pid,
                    "type": meal_type,
                    "name": name,
                    "address": str(data.get("address") or ""),
                    "location": location,
                    "description": str(data.get("note") or "用户添加的餐饮地点"),
                    "estimated_cost": int(round(price)) if price else 0,
                }
            )
            adjusted = True
            adjustment_message = (
                f"已识别为餐饮，加入第{day_index + 1}天餐饮预算"
                if price else f"已识别为餐饮，加入第{day_index + 1}天；未查到价格，未计入预算"
            )
        elif place_type == "attraction":
            day.setdefault("attractions", []).append(
                {
                    "place_id": pid,
                    "name": name,
                    "address": str(data.get("address") or ""),
                    "location": location,
                    "visit_duration": int(data.get("visit_duration_min") or 60),
                    "description": str(data.get("note") or "用户添加的地点"),
                    "category": "用户添加",
                    "photos": [],
                    "poi_id": str(data.get("amap_poi_id") or ""),
                    "ticket_price": int(round(price)) if price else 0,
                }
            )
            adjustment_message = (
                "已加入当日景点预算" if price else "已加入当日景点；未查到价格，未计入预算"
            )
        else:
            adjustment_message = "已保存为地点，不改变当日行程与预算"

    _refresh_plan_budget(plan)
    result = get_place(plan_id, pid) or {}
    result["inferred_type"] = inferred_type
    result["itinerary_adjusted"] = adjusted
    result["adjustment_message"] = adjustment_message
    return result


def update_place(plan_id: str, place_id: str, data: Dict[str, Any], task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    current = get_place(plan_id, place_id)
    if not current:
        return None

    version = data.get("version")
    if version is not None and int(version) != int(current["version"]):
        raise ConflictError("地点已被修改，请刷新后重试")

    location = current["location"]
    if "location" in data:
        location = _valid_location(data["location"])
        if not location:
            raise ValueError("经纬度不合法")

    fields = {
        "name": str(data.get("name", current["name"])).strip(),
        "address": str(data.get("address", current["address"])),
        "note": str(data.get("note", current["note"])),
        "type": str(data.get("type", current["type"])),
        "visit_duration_min": data.get("visit_duration_min", current["visit_duration_min"]),
    }
    if not fields["name"]:
        raise ValueError("地点名称不能为空")
    if fields["type"] not in VALID_TYPES:
        raise ValueError("地点类型不合法")

    conn = _connect()
    try:
        with conn:
            conn.execute(
                "UPDATE places SET name=?, address=?, longitude=?, latitude=?, type=?, note=?,"
                " visit_duration_min=?, updated_at=?, version=version+1 WHERE plan_id=? AND id=?",
                (
                    fields["name"], fields["address"], location["longitude"], location["latitude"],
                    fields["type"], fields["note"], fields["visit_duration_min"], _now(),
                    plan_id, place_id,
                ),
            )
    finally:
        conn.close()

    # 同步回行程 JSON
    plan = _plan_data(task)
    for day in plan.get("days") or []:
        for attraction in day.get("attractions") or []:
            if attraction.get("place_id") == place_id:
                attraction.update(
                    {
                        "name": fields["name"],
                        "address": fields["address"],
                        "location": location,
                        "description": fields["note"] or attraction.get("description", ""),
                    }
                )
        for meal in day.get("meals") or []:
            if meal.get("place_id") == place_id:
                meal.update(
                    {
                        "name": fields["name"],
                        "address": fields["address"],
                        "location": location,
                        "description": fields["note"] or meal.get("description", ""),
                    }
                )
        hotel = day.get("hotel")
        if isinstance(hotel, dict) and hotel.get("place_id") == place_id:
            hotel.update({"name": fields["name"], "address": fields["address"], "location": location})
    _refresh_plan_budget(plan)
    return get_place(plan_id, place_id)


class ConflictError(Exception):
    pass


def delete_place(plan_id: str, place_id: str, task: Dict[str, Any]) -> bool:
    current = get_place(plan_id, place_id)
    if not current:
        return False
    conn = _connect()
    try:
        with conn:
            conn.execute("DELETE FROM places WHERE plan_id = ? AND id = ?", (plan_id, place_id))
    finally:
        conn.close()

    plan = _plan_data(task)
    for day in plan.get("days") or []:
        attractions = day.get("attractions") or []
        day["attractions"] = [
            item for item in attractions if item.get("place_id") != place_id
        ]
        # 用户新增的餐饮会写入 meals，删除地点时也必须同步移除。
        day["meals"] = [
            item for item in (day.get("meals") or [])
            if item.get("place_id") != place_id
        ]
        hotel = day.get("hotel")
        if isinstance(hotel, dict) and hotel.get("place_id") == place_id:
            day["hotel"] = None
    _refresh_plan_budget(plan)
    return True


def reorder_places(plan_id: str, day_index: int, ids: Iterable[str], task: Dict[str, Any]) -> None:
    plan = _plan_data(task)
    days = plan.get("days") or []
    if not (0 <= day_index < len(days)):
        raise ValueError("day_index 不存在")
    id_list = [str(item) for item in ids]
    conn = _connect()
    try:
        with conn:
            for index, pid in enumerate(id_list):
                conn.execute(
                    "UPDATE places SET order_index=?, updated_at=? WHERE plan_id=? AND id=?",
                    (index, _now(), plan_id, pid),
                )
    finally:
        conn.close()
    order = {pid: index for index, pid in enumerate(id_list)}
    day = days[day_index]
    attractions = day.get("attractions") or []
    day["attractions"] = sorted(
        attractions,
        key=lambda item: order.get(str(item.get("place_id")), 9999),
    )


def set_hotel(plan_id: str, day_index: int, place_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
    place = get_place(plan_id, place_id)
    if not place:
        raise ValueError("地点不存在")
    plan = _plan_data(task)
    days = plan.get("days") or []
    if not (0 <= day_index < len(days)):
        raise ValueError("day_index 不存在")

    # 同一天只能有一个酒店；清理旧酒店记录
    old_hotel = days[day_index].get("hotel")
    old_pid = old_hotel.get("place_id") if isinstance(old_hotel, dict) else None
    conn = _connect()
    try:
        with conn:
            if old_pid and old_pid != place_id:
                conn.execute("DELETE FROM places WHERE plan_id=? AND id=?", (plan_id, old_pid))
            conn.execute(
                "UPDATE places SET type='hotel', day_index=?, updated_at=?, version=version+1"
                " WHERE plan_id=? AND id=?",
                (day_index, _now(), plan_id, place_id),
            )
    finally:
        conn.close()

    # 该点若原本是景点/餐饮，移出当日列表，避免同时出现多个类别
    for day in days:
        day["attractions"] = [
            item for item in (day.get("attractions") or [])
            if item.get("place_id") != place_id
        ]
        day["meals"] = [
            item for item in (day.get("meals") or [])
            if item.get("place_id") != place_id
        ]
    price = place.get("price")
    days[day_index]["hotel"] = {
        "place_id": place_id,
        "name": place["name"],
        "address": place["address"],
        "location": place["location"],
        "price_range": f"约 ¥{int(price)}" if price else "",
        "rating": "",
        "distance": "",
        "type": "用户添加",
        "estimated_cost": int(round(float(price))) if price else 0,
    }
    _refresh_plan_budget(plan)
    return get_place(plan_id, place_id) or {}
