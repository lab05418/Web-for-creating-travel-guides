# 重要提醒组件

## 目标

从攻略原文中**复制式抽取**需要提前预约、开放时间、交通衔接、门票/证件等信息，
不删除、不改写任何原字段。抽取结果交给独立组件渲染，可放在概览、每日行程或任何
需要提醒的位置。

## 组件 API

文件：`frontend/src/components/ImportantReminders.vue`

```vue
<ImportantReminders
  :items="reminders"
  heading="行前重要提醒"
  :dense="false"
  :max="6"
  :show-source="true"
/>
```

| Prop | 类型 | 默认 | 说明 |
|---|---|---|---|
| `items` | `ReminderItem[]` | 必填 | 提醒列表；为空时不渲染 DOM |
| `heading` | `string` | 重要提醒 | 组件标题 |
| `dense` | `boolean` | `false` | 紧凑模式，用于每日行程/侧栏 |
| `max` | `number` | `Infinity` | 最多展示条数 |
| `showSource` | `boolean` | `true` | 是否显示来源（第 X 天 · 景点） |

数据契约：`frontend/src/types/reminders.ts`

```ts
interface ReminderItem {
  id: string
  title: string
  description: string
  tone?: 'important' | 'info'
  source?: string
}
```

- 每条提醒固定展示 **标题 + 说明**。
- 同一页面可放置多个实例，样式由组件 scoped CSS 统一。
- 只要列表中有一条 `tone: 'important'`，容器进入高对比提醒样式；纯 `info` 使用中性样式。
- 头部提供 `#actions` 插槽，方便后续加“全部展开/跳转”等操作。

## 抽取规则

文件：`frontend/src/services/reminders.ts`

1. 优先读取 `attraction.reservation_tips`，逐句/逐分句复制；
2. `reservation_required` 但没有 tips 时生成一条通用预约说明；
3. 扫描 `attraction.description`、`day.description`、`day.transfer_info`、
   `overall_suggestions`，只保留命中关键词的原句；
4. 关键词分为：提前预约、开放时间、交通衔接、游览提示；
5. 同一类别下，`tips` 优先于描述，避免“预约提示 + 描述”重复；
6. 按 `description` 去重，标题/来源只是索引，原文说明不改写。

当前插入位置：

- 行程概览：概览卡片下方、景点详解上方；
- 每日行程：当天基础信息之后、景点列表之前。

## 验证

```powershell
# 在开发环境中运行对应的提醒验证脚本，参数为 plan id
```

覆盖：多条提醒、标题/说明、重要样式、来源、跨分区重复实例、原文一致性。
