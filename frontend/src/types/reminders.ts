export type ReminderTone = 'important' | 'info'

/**
 * 提醒组件的唯一数据契约。
 * 组件只负责渲染，不关心提醒来自行程、预约字段还是外部传入。
 */
export interface ReminderItem {
  /** 稳定 id，方便列表 diff 与后续埋点 */
  id: string
  /** 一句话标题，例如「提前预约」「开放时间」 */
  title: string
  /** 原文说明；抽取场景下必须保持与攻略原文一致 */
  description: string
  /** important = 需要突出显示；info = 普通提示 */
  tone?: ReminderTone
  /** 可选来源，例如「第 1 天 · 钟楼」 */
  source?: string
}
