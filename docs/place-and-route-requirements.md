# 地点管理与景区路线呈现 · 实现要求

> 文档性质：需求规格（v1.0），用于指导后续开发与验收  
> 适用页面：`/result`（行程结果页）→「景点地图」  
> 坐标系统：高德 GCJ-02  
> 关联现状：行程数据目前存放在任务 JSON 与 `sessionStorage`，尚无地点 CRUD；公交/地铁路段当前为直线示意。

---

## 0. 现状与差距

| 能力 | 当前实现 | 本要求 |
|---|---|---|
| 地点数据 | 景点、酒店内嵌在 `DayPlan.attractions` / `DayPlan.hotel`，无独立 ID | 独立 `Place` 实体，稳定 ID，可增删改查 |
| 地点新增 | 只能由 AI 生成 | 用户搜索 POI、地图选点、手动录入三种方式 |
| 地点管理 | 无列表、无编辑、无删除 | 地图 + 抽屉双视图，支持编辑/删除/排序/改天 |
| 持久化 | 编辑仅写 `sessionStorage`，刷新或换设备丢失 | 服务端为准，前端缓存；刷新不丢 |
| 驾车/步行路线 | 高德真实道路折线 | 保留并统一线宽、描边、层级 |
| 公交/地铁路线 | `Transfer` 只取时间，路径为起终点直线 | 解析换乘段折线，禁止整段直线 |
| 失败降级 | 直接画起终点直线 | 不允许整段直线；标记不可用或仅短距离步行接驳 |
| 视觉层级 | 单层 Polyline，无描边，标签互相遮挡 | 双层描边、模式配色、选中高亮、标签避让 |

---

## 1. 地点管理

### 1.1 目标

用户可以在结果页自行补充「酒店」和「想去的地点」，并在同一个地图上下文里查看、编辑、删除、排序；所有修改实时反映到地图标记、路线和每日行程，并在刷新后保留。

### 1.2 交互方式

#### 1.2.1 入口

- 地图工具条新增「地点」按钮（与 `3D / 重置` 同组，墨绿激活态；卫星与自动环绕已移除）。
- 桌面端：点击后从右侧滑出 **380px 抽屉**，地图仍可见；选中地点时地图 `panTo` 并高亮标记。
- 移动端（≤768px）：从底部弹出 **bottom sheet**，高度 85vh，可下拉关闭；地图缩放到选中点。
- 抽屉/Sheet 内分两个页签：
  - **地点列表**：按天分组，显示类型图标、名称、地址、坐标、所属天。
  - **添加地点**：搜索、地图选点、手动录入。

#### 1.2.2 新增地点（三种方式）

1. **搜索 POI（推荐）**
   - 输入关键词 + 城市（默认当前行程城市），调用高德 `PlaceSearch`。
   - 结果列表显示名称、地址、距离；选中后自动填充名称/地址/经纬度/`amap_poi_id`。
   - 用户选择类型（酒店/景点/餐饮/车站/自定义）和所属天，保存。
2. **地图选点**
   - 点击「在地图上选点」，地图进入十字准星模式；单击地图取坐标。
   - 调用高德 `Geocoder` 逆地理编码回填地址；名称由用户填写。
3. **手动录入**
   - 表单直接填写名称、地址、经纬度、类型、所属天；坐标必须通过范围校验。

**酒店快捷入口**：每日行程卡片和地点列表中的「设为住宿」；每天最多一个酒店，设置新酒店时提示「替换原酒店」。

#### 1.2.3 查看

- 列表按 `day_index` 分组；顶部筛选：`全部 / 酒店 / 景点 / 餐饮 / 车站 / 自定义`，支持关键词搜索。
- 点击列表项：地图飞行到该点、打开信息窗、列表项高亮。
- 点击地图标记：打开信息卡，显示名称、地址、类型、所属天、备注；卡片提供「编辑 / 删除 / 设为住宿」。
- 空状态：插画 + 「还没有自定义地点」+ 「添加地点」按钮。

#### 1.2.4 编辑

- 列表项或信息卡进入编辑表单，字段与新增一致。
- 支持**拖动标记调整坐标**：进入「调整位置」模式后拖动 Marker，松手写回经纬度（需二次确认）。
- 保存采用乐观更新：先更新本地标记/列表，再发 `PATCH`；失败回滚并 toast。
- 若服务端版本冲突（`409`），提示「该地点已被修改」并拉取最新数据。

#### 1.2.5 删除

- 二次确认；酒店删除提示「删除后将不再显示住宿标记」。
- 删除后：移除标记、失效该点相关路线缓存、重算当日路线。
- 若该点被其他天引用（同一 POI 的不同天副本），只删除当前记录，不影响其他天。

#### 1.2.6 排序与改天

- 列表内拖拽排序（桌面）或「上移/下移」（移动端），写回 `order_index`。
- 「移动到其他天」下拉选择目标天；移动后重算两条路线。
- 排序/改天均走批量接口，失败整体回滚。

### 1.3 数据结构

#### 1.3.1 枚举

```ts
export type PlaceType = 'hotel' | 'attraction' | 'restaurant' | 'station' | 'custom'
export type PlaceSource = 'user' | 'amap' | 'ai'
```

#### 1.3.2 Place 字段

| 字段 | 类型 | 必填 | 约束/说明 |
|---|---|---|---|
| `id` | string (UUID) | 是 | 服务端生成，稳定不变 |
| `plan_id` | string | 是 | 所属行程 |
| `day_index` | int \| null | 否 | 0 起；`null` 表示未分配到某天（仅收藏） |
| `type` | `PlaceType` | 是 | 酒店/景点/餐饮/车站/自定义 |
| `name` | string | 是 | 1–80 字符，去首尾空格 |
| `address` | string | 否 | 0–200 字符；无地址时为空串 |
| `longitude` | float | 是 | −180–180，GCJ-02 |
| `latitude` | float | 是 | −90–90，GCJ-02 |
| `coord_system` | `'GCJ-02'` | 是 | 固定值，避免坐标系混用 |
| `source` | `PlaceSource` | 是 | 用户新增默认 `user` |
| `amap_poi_id` | string \| null | 否 | 高德 POI ID，用于去重/回查 |
| `price` | float \| null | 否 | 高德实时参考价；null 表示无可用价格 |
| `price_source` | string | 否 | `amap` / `plan` / `unavailable` |
| `inferred_type` | string | 否 | 根据名称/POI 类型推断的地点类型 |
| `note` | string | 否 | 0–500 字符 |
| `visit_duration_min` | int \| null | 否 | 建议停留分钟，用于行程/预算 |
| `order_index` | int | 是 | 同一天内从 0 递增 |
| `created_at` | ISO8601 | 是 | UTC |
| `updated_at` | ISO8601 | 是 | UTC |
| `version` | int | 是 | 乐观锁，初始 1 |

#### 1.3.3 Pydantic（后端）

```python
class PlaceType(str, Enum):
    hotel = "hotel"
    attraction = "attraction"
    restaurant = "restaurant"
    station = "station"
    custom = "custom"

class Place(BaseModel):
    id: str
    plan_id: str
    day_index: Optional[int] = None
    type: PlaceType
    name: str = Field(min_length=1, max_length=80)
    address: str = Field(default="", max_length=200)
    location: Location            # 复用现有 longitude / latitude
    coord_system: Literal["GCJ-02"] = "GCJ-02"
    source: Literal["user", "amap", "ai"] = "user"
    amap_poi_id: Optional[str] = None
    note: str = Field(default="", max_length=500)
    visit_duration_min: Optional[int] = Field(default=None, ge=0, le=1440)
    order_index: int = 0
    created_at: datetime
    updated_at: datetime
    version: int = 1
```

#### 1.3.4 JSON 示例

```json
{
  "id": "6d0f5b7e-3f0f-4f0e-9f6e-2b8a1c7d4e21",
  "plan_id": "4fe642c2",
  "day_index": 1,
  "type": "hotel",
  "name": "西安钟楼北大街地铁站酒店",
  "address": "西安市莲湖区北大街西七路291号",
  "location": { "longitude": 108.94774, "latitude": 34.259968 },
  "coord_system": "GCJ-02",
  "source": "user",
  "amap_poi_id": "B0FFG8J9X1",
  "note": "希望安静楼层",
  "visit_duration_min": null,
  "order_index": 0,
  "created_at": "2026-10-29T13:00:00Z",
  "updated_at": "2026-10-29T13:00:00Z",
  "version": 1
}
```

#### 1.3.5 存储模型

**方案 A（推荐，单机/小规模）**：SQLite `backend/data/farway.db`，WAL 模式。

```sql
CREATE TABLE places (
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
  note TEXT NOT NULL DEFAULT '',
  visit_duration_min INTEGER,
  order_index INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX idx_places_plan_day ON places(plan_id, day_index, order_index);
CREATE UNIQUE INDEX uq_places_poi ON places(plan_id, amap_poi_id)
  WHERE amap_poi_id IS NOT NULL;
```

**方案 B（最小改动）**：沿用 `data/trip_tasks/{task_id}.json`，新增 `places: Place[]`，写临时文件后原子替换；适合原型，不推荐长期使用。

#### 1.3.6 与现有行程模型的关系

- 原则：`places` 为**地点真源**；`DayPlan.attractions` / `DayPlan.hotel` 作为兼容视图，由 `places` 派生。
- 迁移：
  1. 首次读取旧计划时，把 `attractions` 逐条转为 `type=attraction` 的 Place（按天/顺序生成 ID），把 `hotel` 转为 `type=hotel`。
  2. 之后地图、列表、路线统一读 `places`。
  3. `TripPlan` 增加可选 `places?: Place[]`，旧客户端忽略该字段。
- 删除/编辑 Place 后，派生视图同步更新；预算中按名称引用的条目需改为按 `place_id` 关联，避免重名。

### 1.4 增删改查接口

统一响应：`{ "success": boolean, "message": string, "data": ... }`。

| 操作 | 方法与路径 | 请求体 | 成功 |
|---|---|---|---|
| 列表 | `GET /api/plans/{plan_id}/places?day_index=&type=` | — | `200` `Place[]` |
| 新增 | `POST /api/plans/{plan_id}/places` | `PlaceCreate` | `201` `Place` |
| 修改 | `PATCH /api/plans/{plan_id}/places/{place_id}` | 部分字段 + `version` | `200` `Place` |
| 删除 | `DELETE /api/plans/{plan_id}/places/{place_id}?version=` | — | `204` |
| 排序 | `PUT /api/plans/{plan_id}/places/order` | `{ day_index, ids: string[] }` | `200` |
| 改天 | `PATCH /api/plans/{plan_id}/places/{place_id}` | `{ day_index, order_index }` | `200` |
| 设酒店 | `PUT /api/plans/{plan_id}/days/{day_index}/hotel` | `{ place_id }` | `200` |

**PlaceCreate**

```json
{
  "day_index": 1,
  "type": "attraction",
  "name": "大唐不夜城",
  "address": "西安市雁塔区慈恩路",
  "location": { "longitude": 108.964, "latitude": 34.218 },
  "source": "amap",
  "amap_poi_id": "B0FFH...",
  "note": "",
  "visit_duration_min": 120
}
```

**错误码**

| 状态 | 场景 |
|---|---|
| `400` | 字段缺失、经纬度越界、`day_index` 不存在 |
| `404` | 计划或地点不存在 |
| `409` | `version` 冲突、同天重复酒店、同计划重复 POI |
| `429` | 公共模式写操作限流 |

### 1.5 持久化与一致性

- 服务端为唯一真源；前端 `sessionStorage` 仅作首屏缓存，写操作成功后以响应覆盖缓存。
- 写操作：**乐观更新 + 失败回滚**；成功后广播 `farway:places-updated`，地图/列表/路线订阅刷新。
- 路线缓存以 `plan_id + day_index + from_place_id + to_place_id + mode` 为 key；地点变更后删除相关 key。
- 并发：`version` 乐观锁；`409` 时拉取最新并提示。
- 公共模式：写接口默认要求 `X-Admin-Token`（与设置接口一致）或登录态；限流复用 `public_guard`。

### 1.6 校验规则

- 名称 1–80 字符；备注 ≤500；地址 ≤200。
- 经度 `[-180,180]`，纬度 `[-90,90]`；拒绝 `NaN/Infinity`。
- 同一天最多 1 个 `hotel`；`order_index` 必须连续去重。
- 同计划内同名且距离 <30m 视为重复，返回 `409` 或提示合并。
- 坐标明显超出当前城市范围时允许保存但提示「该地点距离行程城市较远」。
- 删除仍被路线引用的地点：先删引用并重算，不阻断删除。

### 1.7 验收标准

1. 新增酒店后：地图出现酒店标记、列表「酒店」页签出现该条、刷新页面仍在。
2. 新增景点并选择第 2 天：该点进入第 2 天列表与路线，第 1 天路线不受影响。
3. 编辑名称/坐标：地图标记与路线同步更新，旧路线缓存失效。
4. 删除地点：二次确认后消失，相关路线重算，无残留覆盖物。
5. 拖拽排序后刷新：顺序保持不变。
6. 两个浏览器同时编辑同一地点：后提交者收到 `409` 提示，不生成本地脏数据。
7. 移动端：bottom sheet 可滚动、可关闭，地图不被永久遮挡。

---

## 2. 景区地图导航路线呈现

### 2.1 目标与原则

- **真实**：沿道路/步行道/地铁接驳路径绘制，禁止用起终点直线代替整段路线。
- **清晰**：白描边 + 彩色主线，路线压在地图路网之上但不遮挡 POI。
- **分层**：底图 → 路线描边 → 路线主线 → 选中路线 → 标记 → 标签 → 弹窗。
- **易辨认**：颜色即模式，线型即方式；选中加粗，非选中降透明。
- **性能**：只画当前天；缓存 + 简化；切换天不重复请求。

### 2.2 路线计算

#### 2.2.1 路段生成

对每一天：

1. 读取该天 `places`，按 `order_index` 排序。
2. 生成相邻点路段：`P0→P1, P1→P2, …`。
3. 若当天有酒店且酒店有坐标：
   - 抵达日：`车站 → 酒店` 接驳段（已有）；
   - 可选：`酒店 → 首个景点`、`最后景点 → 酒店`，由配置开关控制（默认关闭，避免线路过密）。
4. 跨城高铁/航班不画城市内路线；只在城际日显示「城际段」标签，不参与市内路径。

#### 2.2.2 方式映射

| 行程 `transportation` / 备注 | 高德服务 | 绘制模式 |
|---|---|---|
| 步行、徒步、散步 | `AMap.Walking` | `walking` |
| 驾车、开车、自驾、打车、出租 | `AMap.Driving`（`LEAST_TIME`） | `driving` |
| 地铁、公交、轻轨、巴士、公共交通 | `AMap.Transfer` | `transit` |
| 骑行、自行车 | `AMap.Riding` | `cycling` |
| 车站→酒店接驳 | 按描述匹配；缺省 `Driving` | `transfer` |
| 其他/无法判断 | 距离 <700m 用 `Walking`，否则 `Driving` | 对应 |

#### 2.2.3 公交换乘折线解析

`AMap.Transfer` 的结果必须解析为折线，不能只取时间：

```ts
const plan = result.plans[0]
const path: [number, number][] = []
for (const seg of plan.segments ?? []) {
  // 步行接驳段
  for (const step of seg.walking?.steps ?? []) {
    path.push(...(step.path ?? parsePolyline(step.polyline)))
  }
  // 公交/地铁段
  for (const step of seg.transit?.steps ?? []) {
    path.push(...(step.path ?? parsePolyline(step.polyline)))
  }
}
```

要求：

- 段与段之间允许 1 条短连接线（≤300m 步行接驳可直连），但**整段路线不得只有起终点两个点**。
- 若 `Transfer` 无路径字段：改用 `Driving` 路线兜底，并标注「公交/地铁 · 预计时间」；仍无路径则标记 `unavailable`，不画直线。
- 所有坐标统一 GCJ-02；去重相邻重复点。

#### 2.2.4 失败与降级

| 情况 | 处理 |
|---|---|
| 路径服务超时/无结果 | 重试 1 次；再失败标记 `unavailable` |
| 距离 <300m 的步行连接 | 允许短直线连接，并标注「步行接驳」 |
| 整段无路径 | 不绘制主线；显示灰色虚线占位 + 「路线暂不可用」标签 |
| 跨城/无城市内道路 | 不画；仅显示城际标签 |

**禁止**：用一条起终点直线冒充驾车/公交/步行路线。

#### 2.2.5 缓存与并发

- 缓存 key：`plan_id|day|from_id|to_id|mode|coordHash`。
- 内存 LRU（≤200 条）+ IndexedDB（24h）；地点/顺序变更时失效。
- 同屏并发 ≤3 个路径请求；切换天/刷新时 `AbortController` 取消旧请求。
- 已缓存路线切换天时立即绘制，不出现空白闪烁。

### 2.3 数据表达

```ts
export type RouteMode = 'walking' | 'driving' | 'transit' | 'cycling' | 'transfer'
export type RouteStatus = 'ready' | 'unavailable'

export interface RouteLeg {
  id: string
  plan_id: string
  day_index: number
  from_place_id: string
  to_place_id: string
  mode: RouteMode
  status: RouteStatus
  path: [number, number][]      // [lng, lat]，GCJ-02，≥2 点
  distance_m: number
  duration_s: number
  steps?: Array<{
    instruction: string
    distance_m: number
    duration_s: number
    polyline: [number, number][]
  }>
  source: 'amap' | 'cache' | 'fallback'
  updated_at: string
}
```

JSON 示例：

```json
{
  "id": "leg_4fe642c2_1_0_1",
  "plan_id": "4fe642c2",
  "day_index": 1,
  "from_place_id": "p_zhonglou",
  "to_place_id": "p_gulou",
  "mode": "walking",
  "status": "ready",
  "path": [[108.9477,34.2599],[108.9468,34.2595],[108.9452,34.2591],[108.9436,34.2593]],
  "distance_m": 620,
  "duration_s": 480,
  "source": "amap",
  "updated_at": "2026-10-29T13:20:00Z"
}
```

- 点数量上限 800；超过用 Douglas–Peucker（容差 1.5–3m）简化。
- 预留编码折线（Google Polyline）可选，JSON 数组为默认。
- 路线可作为 `routes?: RouteLeg[]` 随计划返回，也可前端计算后只存缓存；服务端不强制持久化。

### 2.4 绘制方案

#### 2.4.1 双层描边

每条路段画两层：

1. **描边层（casing）**：白色、较宽，压住底图路网，保证浅色底图也清晰。
2. **主线层（core）**：模式色、较窄，带方向箭头。

#### 2.4.2 层级（z-index）

| 图层 | z-index | 说明 |
|---|---|---|
| 底图 | 0 | 高德瓦片 |
| 路线描边 | 70 | 所有模式 |
| 路线主线 | 80 | 所有模式 |
| 接驳段 | 85 | 车站→酒店，优先于普通段 |
| 选中路线 | 90 | 加粗 + 高亮 |
| 景点/酒店标记 | 120 | 现有标记 |
| 路线标签 | 130 | 胶囊标签 |
| 信息窗/弹窗 | 200 | 最上层 |

#### 2.4.3 线宽与配色标准

| 模式 | 主线色 | 主线宽 | 描边色/宽 | 线型 | 箭头 |
|---|---|---|---|---|---|
| 驾车 `driving` | `#1677FF` | 4px | `#FFFFFF` / 7px | 实线 | 白色 |
| 步行 `walking` | `#00B578` | 3px | `#FFFFFF` / 6px | 虚线 `10,8` | 白色 |
| 公交/地铁 `transit` | `#0F6B4F` | 4px | `#FFFFFF` / 7px | 实线 | 白色 |
| 骑行 `cycling` | `#7C3AED` | 3.5px | `#FFFFFF` / 6.5px | 实线 | 白色 |
| 接驳 `transfer` | `#D97706` | 4px | `#FFFFFF` / 7px | 虚线 `2,6` | 白色 |
| 不可用 `unavailable` | `#9CA3AF` | 2px | 无 | 虚线 `4,6` | 无 |

选中/强调：

- 选中路段主线 +1.5px，描边 +1.5px，透明度 1.0，其余路段透明度 0.35。
- 非当前天路线不绘制（按天筛选）；「全部」模式下同屏最多 3 天，超出提示按天查看。

#### 2.4.4 标签

- 内容：`{模式} 约{分钟}`；接驳段：`接驳·{车站} {模式} 约{分钟}`。
- 样式：白底 94%、1px `#E2DFD5` 边框、圆角 999px、11px/600、墨绿字、轻阴影。
- 位置：路径中点（接驳段放在靠酒店 0.9 处）；按路径长度排序放置。
- 避让：与已放置标签 bbox 相交时，依次尝试 `y-18 / y+18 / x±24`；仍冲突则隐藏该标签（信息窗仍可查看）。
- 缩放 <12 时只保留接驳和最长路段标签；≥15 全量显示。
- 标签不遮挡标记：与标记中心距离 <24px 时偏移。

#### 2.4.5 浅色底图适配

- 使用白色描边，主线颜色不随底图变化，保证模式一致。
- 标签保持白底深字，避免透明底导致不可读。

### 2.5 清晰度标准（验收口径）

1. 任意驾车/步行/公交路段，路径点数 ≥ 5（短于 100m 的步行接驳除外），肉眼可见沿路弯曲。
2. 路线与底图道路重合度：主要路段偏差 ≤ 15m（高德路径本身精度内）。
3. 白色描边完整包住主线，浅色底图无「线淹没在底图」。
4. 同屏路线颜色不超过 3 种模式色；接驳段必须与普通段可区分。
5. 标签不重叠；密集区域允许隐藏，但点击路线/信息卡可查看完整信息。
6. 切换天：旧路线完全清除，无残影；新路线 300ms 内出现（缓存命中）。

### 2.6 性能要求

- 只请求当前选中天；「全部」按天串行/限流绘制。
- 路径点简化到 ≤500 点/段；单天总点数 ≤5000。
- 缓存命中切换 <100ms；首次计算单段 <1.5s。
- 地图刷新/切换天取消未完成请求，避免旧结果覆盖。
- 路线图层统一 `map.add/remove`，不逐条重建地图。

### 2.7 验收场景

1. 西安 2 天行程：第 1 天 3 个景点，第 2 天 4 个景点；每天路线均沿道路，无整段直线。
2. 上海→西安高铁抵达：显示「西安北站→酒店」接驳段，标注「接驳·西安北站 公交/地铁 约35分钟」，路线沿地铁/道路。
3. 切换「第 2 天」：只显示第 2 天标记/路线，第 1 天完全隐藏。
4. 默认底图：路线、标签、标记均清晰可辨。
5. 网络断开：已缓存路线仍显示；未缓存段显示「路线暂不可用」，不出现直线。
6. 移动端 430px：路线不为 0 宽，标签不溢出屏幕，工具条/天筛选可横向滚动。

---

## 3. AI 助手移除

- 已删除左下角浮层组件 `frontend/src/components/AIChat.vue`。
- 已移除 `Result.vue` 中的 `<AIChat />` 与 import。
- 已移除前端 `ChatMessage / TripChatRequest / TripChatResponse` 类型与三语 `result.chat.*` 文案。
- 后端 `/api/chat/ask` 端点保留为可选 API（当前无 UI 入口）；如确认不再需要，可进一步删除 `routes/chat.py`、`chat_service.py` 与对应 schema。
- 验收：结果页左下角无任何悬浮球/聊天入口；构建通过；`AIChat` 引用为 0。

---

## 4. 实施优先级建议

| 阶段 | 内容 |
|---|---|
| P0 | Place 数据模型 + SQLite/JSON 持久化 + 列表/新增/编辑/删除 |
| P0 | 公交/地铁路径解析，去掉整段直线 |
| P1 | 双层描边、模式配色、层级、标签避让 |
| P1 | 地图选点/逆地理编码、拖拽改坐标 |
| P2 | 排序/改天、冲突处理、公共模式权限 |
| P2 | 路线缓存持久化、性能监控 |

---

## 5. 非目标

- 多人实时协作编辑。
- 离线地图/离线路径规划。
- 实时路况、拥堵预测。
- 跨城高铁/航班的真实轨迹绘制。

---

## 6. P0 落地状态（2026-10-29）

已实现：

- 后端 `backend/app/services/place_store.py`：SQLite `backend/data/farway.db`、首次从任务 JSON 迁移、列表/新增/修改/删除/排序/设置酒店；修改会同步写回任务 JSON。
- 后端 `backend/app/api/routes/places.py`：`GET/POST/PATCH/DELETE /api/plans/{plan_id}/places`、排序、设置酒店接口。
- 前端 `frontend/src/services/places.ts` + 结果页「地点」抽屉：列表筛选、添加/编辑/删除、设为住宿、高德 POI 搜索、地图选点 + 逆地理编码。
- 地图：酒店「宿」标记；公交换乘解析 `plan.path`/分段折线，失败时不再整段直线降级；接驳段信息以地图浮层展示。
- 验证：新增/编辑/删除/酒店设置、刷新后持久化、搜索与地图选点均实测通过；UI 断言 27/27。

尚未实现（P1）：

- 双层描边、模式配色与标签碰撞避让的完整视觉规范。
- 列表拖拽排序/改天的完整 UI（后端接口已具备）。
- 地图拖拽标记改坐标、409 冲突的前端提示。
- 写入接口的公共模式权限与限流。

---

## 7. 卫星图与自动环绕已移除（2026-10-30）

**决定**

- 地图工具条只保留「3D / 重置视角 / 地点」，不再加载 `AMap.TileLayer.Satellite`、`AMap.TileLayer.RoadNet`，也不再提供自动环绕按钮与逐帧旋转循环。
- 3D 俯仰与手动旋转仍保留；`resetMapView()` 会回到 45° 俯仰、0° 旋转并适配 marker 视野。

**为什么能降低崩溃概率**

- 卫星模式需要额外创建并切换栅格瓦片图层，`map.setLayers()` 会重建图层树；快速切换或瓦片请求异常时，旧实现容易把切换请求堆在一起并放大 WebGL 上下文压力。
- 自动环绕在每帧写 `setRotation`，会和路线绘制、marker 动画、3D 建筑块共同争抢主线程/GPU；标签页恢复或掉帧时还可能产生相机跳变。
- 移除这两条路径后，地图只保留一个底图图层和手动相机操作，少了「图层反复重建」和「持续逐帧写相机」两类高风险来源，崩溃/卡死概率会下降。但 WebGL 仍受设备 GPU、内存、驱动和 `preserveDrawingBuffer`（导出截图需要）影响，不能承诺绝对不崩溃；上下文丢失时仍由「刷新地图」完整重建兜底。

**验证**

- 结果页地图工具条按钮实测仅为：`3D`、`重置视角`、`地点`。
- 地图仍能加载 canvas、marker 与按天路线，无页面错误。

---

## 8. 地点实时价格、类型推断与导航线修复（2026-10-30）

### 8.1 实时价格与预算

- 新增 `backend/app/services/place_price.py`：通过高德 Place Text / Detail 接口读取 `biz_ext.cost`，按地点类型解释为门票、人均餐饮或参考房价。
- 查询结果写入 `places.price`、`price_source`、`inferred_type`；SQLite 启动时自动为旧库补列。
- 查询失败或没有 `cost` 时返回 `price=None`，地点仍可保存，但**不写入**门票/餐饮/酒店预算；接口返回 `price_available=false` 和调整说明。
- `place_store.create_place()` 按最终类型写入不同的行程位置：
  - `hotel` → 当日 `hotel.estimated_cost`
  - `restaurant` → 当日 `meals[].estimated_cost`
  - `attraction` → 当日 `attractions[].ticket_price`
  - `station/custom` → 仅保存地点，不改变行程与预算
- 用户选择 `custom/attraction` 但高德内容明确是餐饮/住宿/车站时，后端自动纠正类型并返回 `itinerary_adjusted=true`。
- 增删改地点后调用 `_refresh_plan_budget()`，同步任务 JSON 中的预算汇总；前端刷新后重新渲染预算明细。
- 前端保存按钮显示“正在实时查询价格并分析地点类型…”；地图路线刷新时显示“正在重新计算地图路线…”，地点列表加载使用 `a-spin`。

### 8.2 编辑后导航线丢失的根因

旧流程 `refreshAfterPlaceChange()`：

1. `destroyCurrentMap()`；
2. `restoreTripPlanFromResponse()`，其中 `applyTripPlanPayload()` 又调用一次 `ensureMapReady()`；
3. 外层再调用一次 `ensureMapReady()`。

两次初始化会递增 `mapInitGeneration` / `amapRenderToken`，后一次初始化取消前一次尚未完成的路线绘制任务，表现为 marker 还在但导航线消失。

### 8.3 修复

- 地点增删改不再销毁地图，只更新行程数据后调用 `refreshMap()` 重绘覆盖物。
- 仅在 WebGL 上下文丢失等情况下强制重建地图。
- `refreshAfterPlaceChange()` 只保留一次地图刷新入口，避免重复 `ensureMapReady()`。
- 路线绘制仍采用“marker 先显示、路线并发渐进绘制”，并用 token 取消过期任务。

### 8.4 验证

- 添加地点后：地点接口 `201`，预算总额随价格变化；删除后恢复。
- 无价格地点：`price_available=false`，预算不变。
- 地点编辑后：地图仍显示 marker 与导航 Polyline，无页面错误。
- WebGL 上下文丢失后：刷新地图可完整重建并恢复 marker。
- 后端 `test_place_price.py`、`test_places_task_normalization.py` 通过；前端构建通过。

---

## 9. 地图 marker / 酒店 / 路线 / 3D 稳定性修复（2026-10-30）

### 9.1 marker 随机跳动

**原因**

- 每次 `renderMapAttractions()` 都无条件 `map.setFitView()`，即使当前视野已覆盖目标 marker，也会重新适配相机，视觉上像 marker 在跳。
- 地图刷新、切天、选点、取消编辑都可能触发重绘；多个重绘请求叠加时，旧 marker/新 marker 交替出现。
- 不同天的 marker 使用相同的 `zIndex`（都是 `120 + index`），重叠时层级会随添加顺序变化，像“跳来跳去”。

**修复**

- `renderMapAttractions()` 新增 `preserveCamera` / `fitView` 选项：数据刷新时保持相机，只有标记超出当前视野才 `setFitView()`。
- marker 的 `zIndex` 改为 `120 + dayIndex * 100 + index`，酒店为 `160 + dayIndex * 100`，跨天层级稳定。
- 坐标统一 `Number(...)` 后再传给 AMap，避免字符串坐标导致的布局抖动。

### 9.2 切换日期时酒店 marker 乱跳

**原因**

- 每天酒店不同，切天时旧酒店 marker 被清除、新酒店 marker 重建；同时 `setFitView()` 会重新缩放/平移，酒店在屏幕上的位置突然变化。
- 酒店 marker 与景点 marker 共用不稳定的层级，重叠时视觉上会更明显。

**修复**

- 切天时如果当前视野已经覆盖目标天的 marker（包括酒店），不再移动相机，只更新选中天的 marker。
- 酒店 marker 使用按天稳定的 `zIndex`，不再和景点 marker 抢占同一层级。
- 数据刷新/取消编辑使用 `preserveCamera: true`，不会因为一次刷新把用户正在看的位置重置。

### 9.3 导航路线异常消失

**原因**

- `searchRouteDetail()` 把失败结果 `null` 也写进 `routeCache`。高德路径服务短暂限流/超时一次后，该路段在后续所有刷新中都会直接命中 `null` 缓存，永久不画线。
- 重绘时先 `clearAmapRendered()`，路线任务异步补齐；如果此时又发生一次重绘，旧 token 被取消，新任务失败就会表现为“marker 在、路线没了”。
- 路线请求失败时只 `console.warn`，没有重试。

**修复**

- 只缓存成功的路线；失败结果不写入缓存，下一次重绘会重新请求。
- 保留 `amapRenderToken` 取消过期任务，避免旧任务把线画到新状态上。
- 路线仍采用“marker 先显示、路线并发补齐”，但失败不再形成永久空缓存。

### 9.4 取消操作 / 点击 3D 卡死

**原因**

- 3D 切换使用 `setPitch(..., false)` / `setRotation(..., false)` 启动 AMap 内部动画；3D 建筑块 + 大量路线叠加时，动画帧会持续占用主线程/GPU，低端设备上容易表现为点击后长时间无响应。
- `cancelEdit()` 只恢复 `tripPlan`，没有撤销编辑期间地图上的 marker/路线；之后点 3D/刷新会继续叠加旧覆盖物。
- 编辑取消时没有重置 `mapPickMode`，地图可能仍处于选点状态。

**修复**

- 3D/2D 切换改为 AMap 立即模式：`setPitch(..., true)`、`setRotation(..., true)`，一次写完相机，不启动内部动画。
- `toggleMapDimension()` 增加 `cameraAnimating` / `mapLoading` 防重入。
- `cancelEdit()` 恢复行程后重置 `mapPickMode`，并在当前处于地图分区时调用 `refreshMap({ preserveCamera: true })`，撤销编辑期间的地图覆盖物。
- `saveChanges()` 也改为保持相机的刷新，避免保存后地图视角被重置。

### 9.5 验证

- 切天前后 marker 屏幕坐标完全一致（同一相机下），酒店 marker 不再因重新适配视野突然平移。
- 快速连续切换 8 次日期后，导航路线仍存在，无残留 loading。
- 连续点击 3D 5 次，marker 数量稳定，无页面错误。
- 取消编辑后地图重新绘制，marker 数量恢复，无卡死。
