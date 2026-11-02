"""数据模型定义"""

from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import date
from .seat_types import normalize_seat_type


# ============ 请求模型 ============

class CityStay(BaseModel):
    """单城市停留配置"""
    city: str = Field(..., description="城市名称")
    days: int = Field(..., description="在该城市停留天数", ge=1, le=15)


class TripRequest(BaseModel):
    """旅行规划请求"""
    city: str = Field(default="", description="目的地城市(单城市兼容)", example="北京")
    cities: List[CityStay] = Field(default=[], description="多城市行程配置")
    origin: str = Field(default="", description="出发城市(可选)", example="上海")
    intercity_transportation: str = Field(
        default="",
        description="城际交通方式(高铁/火车/飞机/自驾/长途汽车，可选)",
        example="高铁",
    )
    intercity_seat_type: Optional[str] = Field(
        default="二等座",
        description="城际席别；按交通方式使用各自独立分类（高铁/火车/飞机）",
        example="二等座",
    )
    start_date: str = Field(..., description="开始日期 YYYY-MM-DD", example="2025-06-01")
    end_date: str = Field(..., description="结束日期 YYYY-MM-DD", example="2025-06-03")
    travel_days: int = Field(..., description="旅行天数", ge=1, le=30, example=3)
    transportation: str = Field(..., description="交通方式", example="公共交通")
    accommodation: str = Field(..., description="住宿偏好", example="经济型酒店")
    preferences: List[str] = Field(default=[], description="旅行偏好标签", example=["历史文化", "美食"])
    free_text_input: Optional[str] = Field(default="", description="额外要求", example="希望多安排一些博物馆")
    language: Optional[str] = Field(default="zh", description="输出语言(zh/en/ja)", example="en")
    user_id: Optional[str] = Field(default="", description="用户唯一标识(前端生成,用于记忆库)")
    budget_amount: Optional[int] = Field(
        default=None,
        ge=1,
        le=10_000_000,
        description="用户填写的旅游预算(元)；为空表示不限制",
        example=5000,
    )
    include_inter_city_transport_in_budget: bool = Field(
        default=False,
        description="是否将出发地往返/城市间城际交通合并计入旅游总预算",
        example=False,
    )

    @model_validator(mode='after')
    def normalize_cities(self):
        """兼容处理: 如果只填了 city 没填 cities, 自动转换"""
        if not self.cities and self.city:
            self.cities = [CityStay(city=self.city, days=self.travel_days)]
        if self.cities and not self.city:
            self.city = self.cities[0].city
        # 席别随交通方式独立：高铁/火车/飞机用各自分类，自驾/长途汽车为 None。
        self.intercity_seat_type = normalize_seat_type(
            self.intercity_transportation,
            self.intercity_seat_type,
        )
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "city": "北京",
                "cities": [{"city": "北京", "days": 2}, {"city": "西安", "days": 3}],
                "start_date": "2025-06-01",
                "end_date": "2025-06-05",
                "travel_days": 5,
                "transportation": "公共交通",
                "accommodation": "经济型酒店",
                "intercity_transportation": "高铁",
                "intercity_seat_type": "二等座",
                "preferences": ["历史文化", "美食"],
                "free_text_input": "希望多安排一些博物馆",
                "budget_amount": 5000,
                "include_inter_city_transport_in_budget": False
            }
        }


class POISearchRequest(BaseModel):
    """POI搜索请求"""
    keywords: str = Field(..., description="搜索关键词", example="故宫")
    city: str = Field(..., description="城市", example="北京")
    citylimit: bool = Field(default=True, description="是否限制在城市范围内")


class RouteRequest(BaseModel):
    """路线规划请求"""
    origin_address: str = Field(..., description="起点地址", example="北京市朝阳区阜通东大街6号")
    destination_address: str = Field(..., description="终点地址", example="北京市海淀区上地十街10号")
    origin_city: Optional[str] = Field(default=None, description="起点城市")
    destination_city: Optional[str] = Field(default=None, description="终点城市")
    route_type: str = Field(default="walking", description="路线类型: walking/driving/transit")


# ============ 响应模型 ============

class Location(BaseModel):
    """地理位置"""
    longitude: float = Field(..., description="经度")
    latitude: float = Field(..., description="纬度")


# ============ 地点管理 ============

PlaceType = Literal["hotel", "attraction", "restaurant", "station", "custom"]


class PlaceCreate(BaseModel):
    """新增地点请求"""
    day_index: Optional[int] = Field(default=None, ge=0, description="所属天(0起)")
    type: PlaceType = Field(default="custom", description="地点类型")
    name: str = Field(..., min_length=1, max_length=80, description="地点名称")
    address: str = Field(default="", max_length=200, description="地址")
    location: Location = Field(..., description="经纬度(GCJ-02)")
    source: Literal["user", "amap", "ai"] = Field(default="user", description="来源")
    amap_poi_id: Optional[str] = Field(default=None, description="高德 POI ID")
    note: str = Field(default="", max_length=500, description="备注")
    visit_duration_min: Optional[int] = Field(default=None, ge=0, le=1440, description="建议停留分钟")


class PlaceUpdate(BaseModel):
    """修改地点请求（部分字段）"""
    day_index: Optional[int] = Field(default=None, ge=0)
    type: Optional[PlaceType] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    address: Optional[str] = Field(default=None, max_length=200)
    location: Optional[Location] = None
    note: Optional[str] = Field(default=None, max_length=500)
    visit_duration_min: Optional[int] = Field(default=None, ge=0, le=1440)
    version: Optional[int] = Field(default=None, ge=1)


class Attraction(BaseModel):
    """景点信息"""
    name: str = Field(..., description="景点名称")
    address: str = Field(..., description="地址")
    location: Location = Field(..., description="经纬度坐标")
    visit_duration: int = Field(..., description="建议游览时间(分钟)")
    description: str = Field(..., description="景点描述")
    category: Optional[str] = Field(default="景点", description="景点类别")
    rating: Optional[float] = Field(default=None, description="评分")
    photos: Optional[List[str]] = Field(default_factory=list, description="景点图片URL列表")
    poi_id: Optional[str] = Field(default="", description="POI ID")
    image_url: Optional[str] = Field(default=None, description="图片URL")
    ticket_price: int = Field(default=0, description="门票价格(元)")
    reservation_required: Optional[bool] = Field(default=False, description="是否需要提前预约")
    reservation_tips: Optional[str] = Field(default="", description="预约提示信息")


class Meal(BaseModel):
    """餐饮信息"""
    type: str = Field(..., description="餐饮类型: breakfast/lunch/dinner/snack")
    name: str = Field(..., description="餐饮名称")
    address: Optional[str] = Field(default=None, description="地址")
    location: Optional[Location] = Field(default=None, description="经纬度坐标")
    description: Optional[str] = Field(default=None, description="描述")
    estimated_cost: int = Field(default=0, description="预估费用(元)")


class Hotel(BaseModel):
    """酒店信息"""
    name: str = Field(..., description="酒店名称")
    address: str = Field(default="", description="酒店地址")
    location: Optional[Location] = Field(default=None, description="酒店位置")
    price_range: str = Field(default="", description="价格范围")
    rating: str = Field(default="", description="评分")
    distance: str = Field(default="", description="距离景点距离")
    type: str = Field(default="", description="酒店类型")
    estimated_cost: int = Field(default=0, description="预估费用(元/晚)")


class DayPlan(BaseModel):
    """单日行程"""
    date: str = Field(..., description="日期 YYYY-MM-DD")
    day_index: int = Field(..., description="第几天(从0开始)")
    city: str = Field(default="", description="当日所在城市")
    is_transfer_day: bool = Field(default=False, description="是否为城际移动日")
    transfer_info: Optional[str] = Field(default="", description="城际交通信息")
    description: str = Field(..., description="当日行程描述")
    transportation: str = Field(..., description="交通方式")
    accommodation: str = Field(..., description="住宿")
    hotel: Optional[Hotel] = Field(default=None, description="推荐酒店")
    attractions: List[Attraction] = Field(default=[], description="景点列表")
    meals: List[Meal] = Field(default=[], description="餐饮列表")


class WeatherInfo(BaseModel):
    """天气信息"""
    date: str = Field(..., description="日期 YYYY-MM-DD")
    city: str = Field(default="", description="所在城市")
    day_weather: str = Field(default="", description="白天天气")
    night_weather: str = Field(default="", description="夜间天气")
    day_temp: Union[int, str] = Field(default=0, description="白天温度")
    night_temp: Union[int, str] = Field(default=0, description="夜间温度")
    wind_direction: str = Field(default="", description="风向")
    wind_power: str = Field(default="", description="风力")

    @field_validator('day_temp', 'night_temp', mode='before')
    @classmethod
    def parse_temperature(cls, v):
        """解析温度,移除°C等单位"""
        if v is None:
            return 0
        if isinstance(v, str):
            # 移除°C, ℃等单位符号
            v = v.replace('°C', '').replace('℃', '').replace('°', '').strip()
            try:
                return int(v)
            except ValueError:
                return 0
        return v


class Budget(BaseModel):
    """预算信息"""
    total_attractions: int = Field(default=0, description="景点门票总费用")
    total_hotels: int = Field(default=0, description="酒店总费用")
    total_meals: int = Field(default=0, description="餐饮总费用")
    total_transportation: int = Field(default=0, description="交通总费用")
    total_inter_city_transport: int = Field(default=0, description="城际交通总费用")
    total: int = Field(default=0, description="总费用")
    include_inter_city_transport_in_budget: Optional[bool] = Field(
        default=None,
        description="城际交通是否已计入 total；None 表示旧版计划",
    )
    budget_limit: Optional[int] = Field(
        default=None,
        description="用户填写的预算上限；None 表示未限制",
    )
    intercity_transport_mode: Optional[str] = Field(
        default=None,
        description="城际交通方式（用于结果页展示）",
    )
    intercity_seat_type: Optional[str] = Field(
        default=None,
        description="城际席别（二等座/一等座/商务座）",
    )
    intercity_distance_km: Optional[float] = Field(
        default=None,
        description="城际计价里程（公里，往返/联程合计）",
    )
    intercity_ticket_total: Optional[int] = Field(
        default=None,
        description="城际交通参考票价合计（元/人）",
    )
    intercity_pricing_basis: Optional[str] = Field(
        default=None,
        description="城际票价依据：12306_distance_rule / llm_estimate / none",
    )


class TripPlan(BaseModel):
    """旅行计划"""
    city: str = Field(..., description="主城市(兼容)/首个城市")
    cities: List[str] = Field(default=[], description="所有途经城市列表")
    start_date: str = Field(..., description="开始日期")
    end_date: str = Field(..., description="结束日期")
    days: List[DayPlan] = Field(..., description="每日行程")
    weather_info: List[WeatherInfo] = Field(default=[], description="天气信息")
    overall_suggestions: str = Field(..., description="总体建议")
    budget: Optional[Budget] = Field(default=None, description="预算信息")


class TripPlanResponse(BaseModel):
    """旅行计划响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="消息")
    plan_id: Optional[str] = Field(default=None, description="计划ID（与后端任务ID对齐）")
    data: Optional[TripPlan] = Field(default=None, description="旅行计划数据")


class POIInfo(BaseModel):
    """POI信息"""
    id: str = Field(..., description="POI ID")
    name: str = Field(..., description="名称")
    type: str = Field(..., description="类型")
    address: str = Field(..., description="地址")
    location: Location = Field(..., description="经纬度坐标")
    tel: Optional[str] = Field(default=None, description="电话")


class POISearchResponse(BaseModel):
    """POI搜索响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="消息")
    data: List[POIInfo] = Field(default=[], description="POI列表")


class RouteInfo(BaseModel):
    """路线信息"""
    distance: float = Field(..., description="距离(米)")
    duration: int = Field(..., description="时间(秒)")
    route_type: str = Field(..., description="路线类型")
    description: str = Field(..., description="路线描述")


class RouteResponse(BaseModel):
    """路线规划响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="消息")
    data: Optional[RouteInfo] = Field(default=None, description="路线信息")


class WeatherResponse(BaseModel):
    """天气查询响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="消息")
    data: List[WeatherInfo] = Field(default=[], description="天气信息")


# ============ 错误响应 ============

class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = Field(default=False, description="是否成功")
    message: str = Field(..., description="错误消息")
    error_code: Optional[str] = Field(default=None, description="错误代码")


# ============ AI 行程问答模型 ============

class ChatMessage(BaseModel):
    """单条对话消息"""
    role: str = Field(..., description="角色: user / assistant")
    content: str = Field(..., description="消息内容")


class TripChatRequest(BaseModel):
    """行程问答请求"""
    message: str = Field(..., description="用户提问内容")
    trip_plan: dict = Field(..., description="当前旅行计划(JSON对象)")
    history: Optional[List[ChatMessage]] = Field(default=[], description="历史对话记录")


class TripChatResponse(BaseModel):
    """行程问答响应"""
    success: bool = Field(default=True, description="是否成功")
    reply: str = Field(..., description="AI回复内容")
