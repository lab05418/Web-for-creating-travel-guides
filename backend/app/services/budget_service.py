"""预算归一化与城际交通计入规则。

LLM 会输出一份预算汇总，但它可能把城际交通混进市内交通，
也可能把分类小计算错。这里以每日明细为准重新汇总，
并统一执行“城际交通默认不计入总预算”的规则。

城际票价由 ``transport_pricing`` 按 12306 里程规则统一计算；本模块只负责
把报价写进 Budget 元数据，并决定它是否进入 total。
"""

from __future__ import annotations

from typing import Any, Optional

from ..models.schemas import Budget, TripPlan, TripRequest
from ..models.seat_types import normalize_seat_type


def _amount(value: Any) -> int:
    """把 LLM 输出中可能出现的数字/字符串安全地转成非负整数。"""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0
    if numeric <= 0:
        return 0
    return int(round(numeric))


def _sum_plan_items(plan: TripPlan) -> tuple[int, int, int]:
    attractions = 0
    hotels = 0
    meals = 0

    for day in plan.days:
        for attraction in day.attractions:
            attractions += _amount(getattr(attraction, "ticket_price", 0))

        if day.hotel is not None:
            hotels += _amount(getattr(day.hotel, "estimated_cost", 0))

        for meal in day.meals:
            meals += _amount(getattr(meal, "estimated_cost", 0))

    return attractions, hotels, meals


def normalize_budget(
    plan: TripPlan,
    request: TripRequest,
    transport_quote: Optional[Any] = None,
) -> Budget:
    """按统一口径写回 plan.budget，并返回该对象。

    - 门票/酒店/餐饮以每日明细为准重新求和；
    - 市内交通沿用模型估算；
    - 城际交通优先使用 12306 里程规则报价，始终单独统计，只有开关为 True 时才计入 total；
    - 单城市且没有出发地时，不存在城际段，强制为 0。
    """
    existing = plan.budget or Budget()

    attractions, hotels, meals = _sum_plan_items(plan)
    local_transport = _amount(getattr(existing, "total_transportation", 0))

    quote_total = getattr(transport_quote, "ticket_total", None) if transport_quote else None
    if quote_total is not None:
        inter_city = _amount(quote_total)
    else:
        inter_city = _amount(getattr(existing, "total_inter_city_transport", 0))

    city_count = len(request.cities) if request.cities else (1 if request.city else 0)
    if not (request.origin or "").strip() and city_count <= 1:
        inter_city = 0

    include_inter_city = bool(request.include_inter_city_transport_in_budget)
    total = attractions + hotels + meals + local_transport
    if include_inter_city:
        total += inter_city

    mode = (getattr(request, "intercity_transportation", "") or "").strip()
    seat_type = normalize_seat_type(mode, getattr(request, "intercity_seat_type", None))
    if transport_quote is not None:
        pricing_basis = "12306_distance_rule"
        distance_km = getattr(transport_quote, "distance_km", None)
        ticket_total = _amount(quote_total)
    else:
        pricing_basis = existing.intercity_pricing_basis or (
            "llm_estimate" if inter_city > 0 else "none"
        )
        distance_km = existing.intercity_distance_km
        ticket_total = existing.intercity_ticket_total
        if ticket_total is None and inter_city > 0:
            ticket_total = inter_city

    plan.budget = Budget(
        total_attractions=attractions,
        total_hotels=hotels,
        total_meals=meals,
        total_transportation=local_transport,
        total_inter_city_transport=inter_city,
        total=total,
        include_inter_city_transport_in_budget=include_inter_city,
        budget_limit=request.budget_amount,
        intercity_transport_mode=mode or existing.intercity_transport_mode,
        intercity_seat_type=seat_type or existing.intercity_seat_type,
        intercity_distance_km=distance_km,
        intercity_ticket_total=ticket_total,
        intercity_pricing_basis=pricing_basis,
    )
    return plan.budget
