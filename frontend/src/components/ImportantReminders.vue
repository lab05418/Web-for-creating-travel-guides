<template>
  <section
    v-if="visibleItems.length"
    class="important-reminders"
    :class="{ 'is-dense': dense, 'has-important': hasImportant }"
    role="region"
    :aria-label="resolvedHeading"
  >
    <header class="important-reminders__head">
      <span class="important-reminders__icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 3.5l8.5 15H3.5l8.5-15z" />
          <path stroke-linecap="round" d="M12 9v4.2M12 16.2h.01" />
        </svg>
      </span>
      <h4 class="important-reminders__title">{{ resolvedHeading }}</h4>
      <span class="important-reminders__count">{{ visibleItems.length }}</span>
      <span class="important-reminders__spacer"></span>
      <slot name="actions"></slot>
    </header>

    <ul class="important-reminders__list">
      <li
        v-for="item in visibleItems"
        :key="item.id"
        class="important-reminders__item"
        :class="`is-${item.tone || 'important'}`"
      >
        <span class="important-reminders__dot" aria-hidden="true"></span>
        <div class="important-reminders__content">
          <div class="important-reminders__title-row">
            <strong class="important-reminders__item-title">{{ item.title }}</strong>
            <span v-if="showSource && item.source" class="important-reminders__source">{{ item.source }}</span>
          </div>
          <p class="important-reminders__desc">{{ item.description }}</p>
        </div>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { ReminderItem } from '@/types/reminders'

const props = withDefaults(
  defineProps<{
    /** 要渲染的提醒；为空时不渲染任何 DOM */
    items: ReminderItem[]
    /** 标题，默认「重要提醒」 */
    heading?: string
    /** 紧凑模式，用于每日行程/侧栏 */
    dense?: boolean
    /** 最多展示条数，默认全部 */
    max?: number
    /** 是否显示来源（第 X 天 · 景点） */
    showSource?: boolean
  }>(),
  {
    items: () => [],
    heading: '',
    dense: false,
    max: Number.POSITIVE_INFINITY,
    showSource: true,
  }
)

const { t } = useI18n()

const visibleItems = computed(() => props.items.slice(0, props.max))
const hasImportant = computed(() => visibleItems.value.some((item) => (item.tone || 'important') === 'important'))
const resolvedHeading = computed(() => props.heading || t('result.reminders.title'))
</script>

<style scoped lang="scss">
.important-reminders {
  padding: 16px 18px;
  border: 1px solid rgba(15, 107, 79, 0.18);
  border-radius: 14px;
  background: #fff;
  color: var(--fw-text, #1b2420);

  &.has-important {
    border-color: #ecd9b0;
    background: linear-gradient(180deg, #fffaf0 0%, #fffdf8 100%);
  }

  &:not(.has-important) &__icon {
    background: rgba(15, 107, 79, 0.1);
    color: var(--fw-accent, #0f6b4f);
  }

  &:not(.has-important) &__title {
    color: var(--fw-text, #1b2420);
  }

  &:not(.has-important) &__count {
    background: rgba(15, 107, 79, 0.1);
    color: var(--fw-accent, #0f6b4f);
  }

  &__head {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
  }

  &__icon {
    display: grid;
    place-items: center;
    width: 24px;
    height: 24px;
    border-radius: 8px;
    background: rgba(196, 125, 20, 0.12);
    color: #a8640c;

    svg {
      width: 15px;
      height: 15px;
    }
  }

  &__title {
    margin: 0;
    color: #7a4a08;
    font-size: 14px;
    font-weight: 750;
    letter-spacing: 0.02em;
  }

  &__count {
    min-width: 20px;
    padding: 1px 7px;
    border-radius: 999px;
    background: rgba(196, 125, 20, 0.12);
    color: #9a5a06;
    font-size: 11px;
    font-weight: 700;
    text-align: center;
    font-variant-numeric: tabular-nums;
  }

  &__spacer {
    flex: 1;
  }

  &__list {
    display: flex;
    flex-direction: column;
    gap: 9px;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  &__item {
    display: flex;
    gap: 9px;
    align-items: flex-start;
    padding: 9px 11px;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.72);
    border: 1px solid rgba(236, 217, 176, 0.7);

    &.is-info {
      border-color: rgba(15, 107, 79, 0.14);
      background: rgba(255, 255, 255, 0.62);
    }
  }

  &__dot {
    flex: 0 0 auto;
    width: 7px;
    height: 7px;
    margin-top: 6px;
    border-radius: 50%;
    background: #c47d14;
    box-shadow: 0 0 0 3px rgba(196, 125, 20, 0.12);
  }

  &__item.is-info &__dot {
    background: var(--fw-accent, #0f6b4f);
    box-shadow: 0 0 0 3px rgba(15, 107, 79, 0.1);
  }

  &__content {
    min-width: 0;
    flex: 1;
  }

  &__title-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px 9px;
    margin-bottom: 3px;
  }

  &__item-title {
    color: #5d3a08;
    font-size: 12.5px;
    font-weight: 750;
    line-height: 1.4;
  }

  &__item.is-info &__item-title {
    color: var(--fw-text, #1b2420);
  }

  &__source {
    padding: 1px 7px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.8);
    border: 1px solid rgba(196, 125, 20, 0.16);
    color: #8b5a13;
    font-size: 10.5px;
    line-height: 1.5;
    white-space: nowrap;
  }

  &__item.is-info &__source {
    border-color: rgba(15, 107, 79, 0.14);
    color: var(--fw-text-3, #8a938c);
  }

  &__desc {
    margin: 0;
    color: #6a4a1c;
    font-size: 12.5px;
    line-height: 1.75;
  }

  &__item.is-info &__desc {
    color: var(--fw-text-2, #5c675f);
  }

  &.is-dense {
    padding: 12px 14px;
    border-radius: 12px;
  }

  &.is-dense &__head {
    margin-bottom: 8px;
  }

  &.is-dense &__item {
    padding: 7px 9px;
  }

  &.is-dense &__desc {
    font-size: 12px;
    line-height: 1.65;
  }
}

@media (max-width: 640px) {
  .important-reminders {
    padding: 13px 13px 12px;

    &__desc {
      font-size: 12px;
    }

    &__source {
      white-space: normal;
    }
  }
}
</style>
