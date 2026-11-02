<template>
  <article class="attraction-card">
    <div class="attraction-card__media">
      <img
        :src="imageSrc"
        :alt="item.name"
        loading="lazy"
        decoding="async"
        referrerpolicy="no-referrer"
        @error="emit('image-error', $event)"
      />
      <button
        type="button"
        class="attraction-card__media-hit"
        :title="t('result.attractionDetail.openNamed', { name: item.name })"
        :aria-label="t('result.attractionDetail.openNamed', { name: item.name })"
        @click="emit('open-detail')"
      ></button>
      <span class="attraction-card__day">{{ t('common.dayNumber', { day: item.dayNumber }) }}</span>
      <span v-if="item.category" class="attraction-card__category">{{ item.category }}</span>
      <span class="attraction-card__shade"></span>
      <span class="attraction-card__hint">{{ t('result.attractionDetail.open') }}</span>
    </div>

    <div class="attraction-card__body">
      <div class="attraction-card__head">
        <h3 class="attraction-card__title">{{ item.name }}</h3>
        <span v-if="item.ticket_price" class="attraction-card__price">
          <span>¥{{ item.ticket_price }}</span>
          <em>{{ t('result.referenceOnly') }}</em>
        </span>
      </div>
      <p class="attraction-card__desc">{{ item.description || item.address || t('common.noData') }}</p>

      <div class="attraction-card__meta">
        <span class="attraction-card__meta-item">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">
            <circle cx="12" cy="12" r="8.5" />
            <path stroke-linecap="round" d="M12 7.5V12l3 1.8" />
          </svg>
          {{ t('result.attractionDetail.duration', { minutes: item.visit_duration }) }}
        </span>
        <span v-if="item.address" class="attraction-card__meta-item attraction-card__meta-item--address">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 21s6-5.1 6-10a6 6 0 10-12 0c0 4.9 6 10 6 10z" />
            <circle cx="12" cy="11" r="2" />
          </svg>
          {{ item.address }}
        </span>
      </div>

      <button
        type="button"
        class="attraction-card__action"
        data-testid="overview-enter"
        :data-attraction-name="item.name"
        @click="emit('open-detail')"
      >
        <span>{{ t('result.attractionDetail.open') }}</span>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5 12h13M13 6.5l5.5 5.5L13 17.5" />
        </svg>
      </button>
    </div>
  </article>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

type OverviewAttractionItem = {
  name: string
  address: string
  visit_duration: number
  description: string
  category?: string
  ticket_price?: number
  dayNumber: number
  dayArrayIndex: number
  order: number
}

defineProps<{
  item: OverviewAttractionItem
  imageSrc: string
}>()

const emit = defineEmits<{
  (e: 'open-detail'): void
  (e: 'image-error', event: Event): void
}>()

const { t } = useI18n()
</script>

<style scoped lang="scss">
.attraction-card {
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100%;
  overflow: hidden;
  border: 1px solid var(--fw-border, #e2dfd5);
  border-radius: 16px;
  background: var(--fw-surface, #fff);
  box-shadow: 0 10px 26px -22px rgba(27, 36, 32, 0.4);
  transition:
    transform 0.22s ease,
    box-shadow 0.22s ease,
    border-color 0.22s ease;

  &:hover {
    transform: translateY(-3px);
    border-color: rgba(15, 107, 79, 0.35);
    box-shadow: 0 20px 36px -24px rgba(27, 36, 32, 0.42);
  }

  &__media {
    position: relative;
    aspect-ratio: 4 / 3;
    overflow: hidden;
    background: #e9e6dc;

    img {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform 0.5s ease;
    }
  }

  &:hover &__media img {
    transform: scale(1.035);
  }

  &__media-hit {
    position: absolute;
    inset: 0;
    z-index: 3;
    padding: 0;
    border: 0;
    background: transparent;
    cursor: pointer;

    &:focus-visible {
      outline: 3px solid rgba(15, 107, 79, 0.6);
      outline-offset: -4px;
    }
  }

  &__day,
  &__category {
    position: absolute;
    z-index: 4;
    top: 12px;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 650;
    line-height: 1.4;
    pointer-events: none;
    backdrop-filter: blur(6px);
  }

  &__day {
    left: 12px;
    background: rgba(15, 107, 79, 0.92);
    color: #fff;
    letter-spacing: 0.02em;
  }

  &__category {
    right: 12px;
    background: rgba(255, 255, 255, 0.92);
    color: var(--fw-text-2, #5c675f);
  }

  &__shade {
    position: absolute;
    inset: 45% 0 0;
    z-index: 1;
    background: linear-gradient(180deg, transparent, rgba(15, 25, 20, 0.58));
    opacity: 0;
    transition: opacity 0.22s ease;
    pointer-events: none;
  }

  &__hint {
    position: absolute;
    right: 14px;
    bottom: 12px;
    z-index: 2;
    padding: 5px 11px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.94);
    color: var(--fw-accent, #0f6b4f);
    font-size: 11.5px;
    font-weight: 650;
    opacity: 0;
    transform: translateY(4px);
    transition:
      opacity 0.22s ease,
      transform 0.22s ease;
    pointer-events: none;
  }

  &:hover &__shade,
  &:focus-within &__shade,
  &:hover &__hint,
  &:focus-within &__hint {
    opacity: 1;
    transform: translateY(0);
  }

  &__body {
    display: flex;
    flex: 1;
    flex-direction: column;
    padding: 16px 17px 17px;
  }

  &__head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 10px;
  }

  &__title {
    margin: 0;
    color: var(--fw-text, #1b2420);
    font-size: 19px;
    font-weight: 750;
    letter-spacing: 0.01em;
    line-height: 1.35;
  }

  &__price {
    flex: 0 0 auto;
    display: inline-flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 1px;
    padding: 3px 8px;
    border-radius: 6px;
    background: rgba(15, 107, 79, 0.08);
    color: var(--fw-accent, #0f6b4f);
    font-size: 11.5px;
    font-weight: 700;
    line-height: 1.25;

    em {
      font-style: normal;
      font-size: 8.5px;
      font-weight: 500;
      opacity: 0.78;
    }
  }

  &__desc {
    display: -webkit-box;
    margin: 8px 0 12px;
    overflow: hidden;
    color: var(--fw-text-2, #5c675f);
    font-size: 13px;
    line-height: 1.7;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    line-clamp: 2;
  }

  &__meta {
    display: flex;
    flex-wrap: wrap;
    gap: 5px 10px;
    margin-bottom: 14px;
  }

  &__meta-item {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    max-width: 100%;
    min-width: 0;
    color: var(--fw-text-3, #8a938c);
    font-size: 11.5px;
    line-height: 1.5;

    svg {
      flex: 0 0 auto;
      width: 13px;
      height: 13px;
    }

    &--address {
      flex: 1 1 100%;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }
  }

  &__action {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    width: 100%;
    height: 40px;
    margin-top: auto;
    padding: 0 13px;
    border: 1px solid var(--fw-accent, #0f6b4f);
    border-radius: 9px;
    background: transparent;
    color: var(--fw-accent, #0f6b4f);
    font-size: 12.5px;
    font-weight: 700;
    cursor: pointer;
    transition:
      background 0.18s ease,
      color 0.18s ease;

    svg {
      width: 17px;
      height: 17px;
      transition: transform 0.18s ease;
    }

    &:hover,
    &:focus-visible {
      background: var(--fw-accent, #0f6b4f);
      color: #fff;
      outline: none;

      svg {
        transform: translateX(3px);
      }
    }
  }
}

@media (max-width: 520px) {
  .attraction-card {
    &__title {
      font-size: 18px;
    }

    &__body {
      padding: 14px 15px 15px;
    }
  }
}

@media (prefers-reduced-motion: reduce) {
  .attraction-card,
  .attraction-card__media img,
  .attraction-card__action svg {
    transition: none;
  }
}
</style>
