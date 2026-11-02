import type { Attraction, DayPlan, TripPlan } from '@/types'
import type { ReminderItem, ReminderTone } from '@/types/reminders'

export interface PlanReminder extends ReminderItem {
  dayIndex: number
}

type ReminderRule = {
  pattern: RegExp
  title: string
  tone: ReminderTone
}

/**
 * 只负责「识别哪些原句属于重要提醒」，不修改原句。
 * 标题是整理出来的索引，description 始终保留攻略原文。
 */
const REMINDER_RULES: ReminderRule[] = [
  {
    pattern: /预约|实名制|实名|限流|约满|提前.{0,6}(购票|买票|抢票)/,
    title: '提前预约',
    tone: 'important',
  },
  {
    pattern: /开放时间|营业时间|闭馆|闭园|开园|停止入场|停止售票|最晚.{0,4}(入场|入园)|周一闭馆/,
    title: '开放时间',
    tone: 'important',
  },
  {
    pattern:
      /末班|车次|航班|高铁|动车|机场|接驳|安检|换乘|提前.{0,4}小时|返程.{0,20}(高铁|动车|航班|机场|车站|车次|票)/,
    title: '交通衔接',
    tone: 'info',
  },
  {
    pattern: /门票|票价|联票|套票|讲解|证件|身份证|优惠|免票|儿童票|学生票/,
    title: '游览提示',
    tone: 'info',
  },
  {
    pattern: /重要提醒|特别提醒|温馨提示|参观须知|出行提示|游客须知/,
    title: '重要提醒',
    tone: 'important',
  },
]

const splitSentences = (text?: string | null): string[] => {
  const raw = String(text || '').trim()
  if (!raw) return []
  const matched = raw.match(/[^。！？!?；;\n，,]+[。！？!?；;，,]?/g)
  return (matched || [raw]).map((item) => item.trim()).filter(Boolean)
}

const normalizeText = (text: string): string => text.replace(/[\s，。！？!?；;、：:"'“”‘’]/g, '').toLowerCase()

const hashText = (text: string): string => {
  let hash = 5381
  for (let index = 0; index < text.length; index += 1) {
    hash = (hash * 33) ^ text.charCodeAt(index)
  }
  return (hash >>> 0).toString(36)
}

const matchRule = (sentence: string): ReminderRule | null =>
  REMINDER_RULES.find((rule) => rule.pattern.test(sentence)) || null

const buildReminder = (
  dayIndex: number,
  source: string,
  title: string,
  description: string,
  tone: ReminderTone
): PlanReminder => ({
  id: `reminder-${dayIndex}-${hashText(`${title}|${description}`)}`,
  dayIndex,
  title,
  description,
  tone,
  source,
})

const collectTextReminders = (
  text: string | null | undefined,
  dayIndex: number,
  source: string,
  fallbackTitle: string,
  fallbackTone: ReminderTone
): PlanReminder[] => {
  const reminders: PlanReminder[] = []
  for (const sentence of splitSentences(text)) {
    const rule = matchRule(sentence)
    reminders.push(
      buildReminder(
        dayIndex,
        source,
        rule?.title || fallbackTitle,
        sentence,
        rule?.tone || fallbackTone
      )
    )
  }
  return reminders
}

const dedupeReminders = (reminders: PlanReminder[]): PlanReminder[] => {
  const seen = new Set<string>()
  return reminders.filter((item) => {
    const key = `${item.dayIndex}|${normalizeText(item.description)}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

const extractAttractionReminders = (
  attraction: Attraction,
  dayIndex: number
): PlanReminder[] => {
  const dayLabel = `第 ${dayIndex + 1} 天`
  const source = `${dayLabel} · ${attraction.name}`
  const reminders: PlanReminder[] = []
  const tips = String(attraction.reservation_tips || '').trim()
  const coveredTitles = new Set<string>()

  if (tips) {
    // 预约提示本身就是攻略原文，逐句复制，不合并、不改写
    const tipReminders = collectTextReminders(tips, dayIndex, source, '预约提示', 'important')
    tipReminders.forEach((item) => coveredTitles.add(item.title))
    reminders.push(...tipReminders)
  } else if (attraction.reservation_required) {
    reminders.push(
      buildReminder(
        dayIndex,
        source,
        '需要提前预约',
        '该景点需要提前预约，请出发前确认预约渠道。',
        'important'
      )
    )
    coveredTitles.add('需要提前预约')
  }

  // 攻略描述里常会重复 tips 的内容；相同类别的提醒只保留 tips 版本，
  // 但描述里额外的开放时间/交通信息仍会保留。
  reminders.push(
    ...collectTextReminders(
      attraction.description,
      dayIndex,
      source,
      '景点提示',
      attraction.reservation_required ? 'important' : 'info'
    ).filter((item) => {
      if (item.title === '景点提示' && !matchRule(item.description)) return false
      return !coveredTitles.has(item.title)
    })
  )

  return reminders
}

const extractDayReminders = (day: DayPlan, dayIndex: number): PlanReminder[] => {
  const source = `第 ${dayIndex + 1} 天 · 行程安排`
  const reminders: PlanReminder[] = []
  // 日描述通常很长，只取命中关键词的原句，避免把普通行程描述也变成提醒
  const descriptionReminders = collectTextReminders(
    day.description,
    dayIndex,
    source,
    '行程提示',
    'info'
  ).filter((item) => matchRule(item.description))
  reminders.push(...descriptionReminders)

  // transfer_info 常与日描述重复（例如都写“乘高铁抵达”），同类别只保留描述版本
  const coveredTitles = new Set(descriptionReminders.map((item) => item.title))
  reminders.push(
    ...collectTextReminders(day.transfer_info, dayIndex, source, '交通衔接', 'info').filter(
      (item) => matchRule(item.description) && !coveredTitles.has(item.title)
    )
  )
  return reminders
}

/**
 * 从整份攻略里抽取提醒。每条提醒的 description 都来自原攻略文本；
 * 仅新增 title/tone/source 这类索引信息，原字段保持原样。
 */
export const extractPlanReminders = (plan: TripPlan): PlanReminder[] => {
  const reminders: PlanReminder[] = []

  plan.days.forEach((day, dayIndex) => {
    day.attractions.forEach((attraction) => {
      reminders.push(...extractAttractionReminders(attraction, dayIndex))
    })
    reminders.push(...extractDayReminders(day, dayIndex))
  })

  reminders.push(
    ...collectTextReminders(
      plan.overall_suggestions,
      -1,
      '行程建议',
      '行前提示',
      'info'
    ).filter((item) => matchRule(item.description))
  )

  return dedupeReminders(reminders)
}
