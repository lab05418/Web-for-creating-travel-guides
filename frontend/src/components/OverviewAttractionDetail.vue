<template>
  <section
    id="overview-attraction-detail"
    class="attraction-detail"
    :aria-label="item.name"
    aria-live="polite"
  >
    <button class="detail-close" type="button" :title="t('result.attractionDetail.close')" @click="emit('close')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">
        <path stroke-linecap="round" d="M6 6l12 12M18 6L6 18" />
      </svg>
    </button>

    <header class="detail-head">
      <div class="detail-eyebrow">
        <span class="detail-day">{{ dayLabel || t('common.dayNumber', { day: item.dayNumber }) }}</span>
        <span v-if="item.category" class="detail-category">{{ item.category }}</span>
        <span class="detail-kicker">{{ t('result.attractionDetail.eyebrow') }}</span>
      </div>
      <h3 class="detail-title">{{ item.name }}</h3>
      <p v-if="item.address" class="detail-address">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 21s6-5.1 6-10a6 6 0 10-12 0c0 4.9 6 10 6 10z" />
          <circle cx="12" cy="11" r="2.2" />
        </svg>
        {{ item.address }}
      </p>
      <div class="detail-meta">
        <span>{{ t('result.attractionDetail.duration', { minutes: item.visit_duration }) }}</span>
        <span v-if="priceKnown !== false && item.ticket_price">{{ t('result.attractionDetail.ticket', { price: item.ticket_price }) }}</span>
        <span v-else-if="priceKnown !== false">{{ t('result.attractionDetail.free') }}</span>
        <span v-else>{{ t('result.attractionDetail.priceUnknown') }}</span>
      </div>
    </header>

    <div v-if="heroImage" class="detail-gallery">
      <img
        class="detail-gallery__hero"
        :src="heroImage"
        :alt="item.name"
        loading="eager"
        decoding="async"
        referrerpolicy="no-referrer"
        @error="markImageFailed(heroImage)"
      />
      <div v-if="thumbImages.length" class="detail-gallery__thumbs">
        <img
          v-for="src in thumbImages"
          :key="src"
          :src="src"
          :alt="`${item.name} 实拍`"
          loading="lazy"
          decoding="async"
          referrerpolicy="no-referrer"
          @error="markImageFailed(src)"
        />
      </div>
    </div>

    <div v-if="loading" class="detail-loading">
      <div class="detail-loading-text">
        <span class="detail-loading-dot"></span>
        {{ t('result.attractionDetail.loading') }}
      </div>
      <div class="detail-skeleton detail-skeleton--lead"></div>
      <div class="detail-skeleton"></div>
      <div class="detail-skeleton detail-skeleton--short"></div>
      <div class="detail-loading-hint">{{ t('result.attractionDetail.loadingHint') }}</div>
    </div>

    <div v-else-if="error" class="detail-error">
      <p>{{ error }}</p>
      <button type="button" class="detail-retry" @click="emit('retry')">
        {{ t('result.attractionDetail.retry') }}
      </button>
    </div>

    <div v-else-if="guide" class="detail-body">
      <p v-if="guide.overview" class="detail-overview">{{ guide.overview }}</p>

      <div class="detail-columns">
        <div class="detail-main">
          <section class="detail-section">
            <div class="detail-section-head">
              <span class="detail-section-no">01</span>
              <h4>{{ t('result.attractionDetail.history') }}</h4>
              <span class="detail-section-line"></span>
            </div>
            <p class="detail-history">{{ guide.history }}</p>
          </section>

          <section v-if="guide.fun_facts?.length" class="detail-section">
            <div class="detail-section-head">
              <span class="detail-section-no">02</span>
              <h4>{{ t('result.attractionDetail.fun') }}</h4>
              <span class="detail-section-line"></span>
            </div>
            <ul class="detail-fun-list">
              <li v-for="(fact, index) in guide.fun_facts" :key="index">
                <span class="detail-fun-dot"></span>
                <p>{{ fact }}</p>
              </li>
            </ul>
          </section>
        </div>

        <aside v-if="guide.tips?.length" class="detail-aside">
          <div class="detail-section-head">
            <span class="detail-section-no">03</span>
            <h4>{{ t('result.attractionDetail.tips') }}</h4>
          </div>
          <ul class="detail-tip-list">
            <li v-for="(tip, index) in guide.tips" :key="index">{{ tip }}</li>
          </ul>
          <p class="detail-aside-note">{{ t('result.attractionDetail.note') }}</p>
        </aside>
      </div>

      <p v-if="guide.source === 'fallback'" class="detail-source">
        {{ t('result.attractionDetail.sourceFallback') }}
      </p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { AttractionGuide } from '@/services/attractionGuide'

type DetailItem = {
  name: string
  address: string
  visit_duration: number
  description: string
  ticket_price?: number
  category?: string
  dayNumber: number
  dayArrayIndex: number
  order: number
}

const props = defineProps<{
  item: DetailItem
  images?: string[]
  guide: AttractionGuide | null
  loading: boolean
  error: string
  dayLabel?: string
  priceKnown?: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'retry'): void
}>()

const { t } = useI18n()

const failedImages = ref<string[]>([])
const orderedImages = ref<string[]>([])
let imageOrderToken = 0

// 高德图库不保证第一张分辨率最高；预加载后按实际像素面积排序，
// 让详情大图优先使用最清晰的一张。
watch(
  [() => props.item.name, () => props.images],
  async ([, images]) => {
    const token = ++imageOrderToken
    const list = (images || []).filter(Boolean)
    failedImages.value = []
    orderedImages.value = list

    const metas = await Promise.all(
      list.map(
        (src) =>
          new Promise<{ src: string; area: number }>((resolve) => {
            if (typeof Image === 'undefined' || src.startsWith('data:')) {
              resolve({ src, area: 0 })
              return
            }
            const image = new Image()
            image.onload = () => resolve({ src, area: image.naturalWidth * image.naturalHeight })
            image.onerror = () => resolve({ src, area: 0 })
            image.src = src
          })
      )
    )
    if (token !== imageOrderToken) return

    const valid = metas.filter((item) => item.area > 0).sort((a, b) => b.area - a.area)
    orderedImages.value = valid.length > 0 ? valid.map((item) => item.src) : list
  },
  { immediate: true }
)

const visibleImages = computed(() =>
  orderedImages.value.filter((src) => src && !failedImages.value.includes(src))
)
const heroImage = computed(() => visibleImages.value[0] || '')
const thumbImages = computed(() => visibleImages.value.slice(1, 3))

const markImageFailed = (src: string) => {
  if (!failedImages.value.includes(src)) {
    failedImages.value = [...failedImages.value, src]
  }
}
</script>

<style scoped lang="scss">
.attraction-detail {
  position: relative;
  margin: 8px 0 22px;
  scroll-margin-top: 92px;
  padding: 30px 34px 28px;
  border: 1px solid var(--fw-border, #e2dfd5);
  border-radius: 18px;
  background:
    radial-gradient(circle at 100% 0%, rgba(15, 107, 79, 0.06), transparent 34%),
    var(--fw-surface-2, #fbfaf6);
  box-shadow: 0 18px 46px -30px rgba(27, 36, 32, 0.35);
  animation: detail-in 0.34s cubic-bezier(0.22, 0.8, 0.3, 1) both;

  &::before {
    content: '';
    position: absolute;
    top: 30px;
    bottom: 30px;
    left: -1px;
    width: 3px;
    border-radius: 0 3px 3px 0;
    background: linear-gradient(180deg, var(--fw-accent, #0f6b4f), rgba(15, 107, 79, 0.08));
  }
}

@keyframes detail-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.detail-close {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 32px;
  height: 32px;
  padding: 6px;
  border: 1px solid transparent;
  border-radius: 50%;
  background: transparent;
  color: var(--fw-text-3, #8a938c);
  cursor: pointer;
  transition: all 0.18s ease;

  svg {
    width: 100%;
    height: 100%;
  }

  &:hover {
    border-color: var(--fw-border, #e2dfd5);
    background: #fff;
    color: var(--fw-text, #1b2420);
  }
}

.detail-head {
  padding-right: 40px;
}

.detail-eyebrow {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.detail-day {
  padding: 3px 9px;
  border-radius: 999px;
  background: var(--fw-accent, #0f6b4f);
  color: #fff;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.detail-category {
  padding: 3px 9px;
  border: 1px solid var(--fw-border, #e2dfd5);
  border-radius: 999px;
  color: var(--fw-text-2, #5c675f);
  background: rgba(255, 255, 255, 0.7);
}

.detail-kicker {
  color: var(--fw-accent, #0f6b4f);
  font-weight: 700;
}

.detail-title {
  margin: 10px 0 4px;
  color: var(--fw-text, #1b2420);
  font-family: 'Noto Serif SC', 'Songti SC', 'STSong', serif;
  font-size: clamp(25px, 2.6vw, 34px);
  font-weight: 700;
  letter-spacing: 0.015em;
  line-height: 1.25;
}

.detail-address {
  display: flex;
  align-items: center;
  gap: 5px;
  margin: 0;
  color: var(--fw-text-3, #8a938c);
  font-size: 12.5px;
  line-height: 1.6;

  svg {
    flex: 0 0 auto;
    width: 14px;
    height: 14px;
  }
}

.detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;

  span {
    padding: 4px 10px;
    border-radius: 6px;
    background: rgba(15, 107, 79, 0.07);
    color: var(--fw-accent, #0f6b4f);
    font-size: 12px;
    line-height: 1.5;
  }
}

.detail-gallery {
  display: grid;
  gap: 10px;
  width: 100%;
  max-width: 960px;
  margin: 20px auto 0;
}

.detail-gallery__hero {
  width: 100%;
  height: clamp(210px, 30vw, 400px);
  object-fit: cover;
  border: 1px solid var(--fw-border, #e2dfd5);
  border-radius: 12px;
  background: #e9e6dc;
}

.detail-gallery__thumbs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;

  img {
    width: 100%;
    height: clamp(110px, 15vw, 200px);
    object-fit: cover;
    border: 1px solid var(--fw-border, #e2dfd5);
    border-radius: 10px;
    background: #e9e6dc;
  }

  img:only-child {
    grid-column: span 2;
    height: clamp(140px, 20vw, 260px);
  }
}

.detail-overview {
  margin: 20px 0 4px;
  padding: 16px 20px;
  border-left: 2px solid rgba(15, 107, 79, 0.35);
  background: rgba(255, 255, 255, 0.66);
  border-radius: 0 10px 10px 0;
  color: var(--fw-text, #1b2420);
  font-size: 15px;
  font-weight: 500;
  line-height: 1.9;
}

.detail-columns {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(240px, 0.85fr);
  gap: 34px;
  margin-top: 22px;
}

.detail-section + .detail-section {
  margin-top: 26px;
  padding-top: 24px;
  border-top: 1px dashed var(--fw-border, #e2dfd5);
}

.detail-section-head {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 12px;

  h4 {
    margin: 0;
    color: var(--fw-text, #1b2420);
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.02em;
  }
}

.detail-section-no {
  color: rgba(15, 107, 79, 0.52);
  font-family: 'Raleway', sans-serif;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.detail-section-line {
  flex: 1;
  height: 1px;
  background: var(--fw-border, #e2dfd5);
}

.detail-history {
  margin: 0;
  color: var(--fw-text-2, #5c675f);
  font-size: 14px;
  line-height: 2;
  text-align: justify;
}

.detail-fun-list {
  display: flex;
  flex-direction: column;
  gap: 11px;
  margin: 0;
  padding: 0;
  list-style: none;

  li {
    display: flex;
    gap: 10px;
    align-items: flex-start;
  }

  p {
    margin: 0;
    color: var(--fw-text-2, #5c675f);
    font-size: 13.5px;
    line-height: 1.8;
  }
}

.detail-fun-dot {
  flex: 0 0 auto;
  width: 6px;
  height: 6px;
  margin-top: 9px;
  border-radius: 50%;
  background: var(--fw-accent, #0f6b4f);
  box-shadow: 0 0 0 3px rgba(15, 107, 79, 0.1);
}

.detail-aside {
  align-self: start;
  padding: 18px 18px 16px;
  border: 1px solid var(--fw-border, #e2dfd5);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.72);
}

.detail-tip-list {
  margin: 0;
  padding: 0;
  list-style: none;
  counter-reset: tips;

  li {
    position: relative;
    padding-left: 24px;
    color: var(--fw-text-2, #5c675f);
    font-size: 12.5px;
    line-height: 1.75;

    & + li {
      margin-top: 9px;
    }

    &::before {
      counter-increment: tips;
      content: counter(tips);
      position: absolute;
      top: 2px;
      left: 0;
      display: grid;
      place-items: center;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: rgba(15, 107, 79, 0.09);
      color: var(--fw-accent, #0f6b4f);
      font-size: 9px;
      font-weight: 700;
    }
  }
}

.detail-aside-note {
  margin: 14px 0 0;
  padding-top: 12px;
  border-top: 1px dashed var(--fw-border, #e2dfd5);
  color: var(--fw-text-3, #8a938c);
  font-size: 11px;
  line-height: 1.6;
}

.detail-loading {
  margin-top: 22px;
}

.detail-loading-text {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 16px;
  color: var(--fw-accent, #0f6b4f);
  font-size: 13px;
  font-weight: 600;
}

.detail-loading-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  animation: detail-pulse 1.1s ease-in-out infinite;
}

@keyframes detail-pulse {
  0%,
  100% {
    opacity: 0.25;
    transform: scale(0.8);
  }
  50% {
    opacity: 1;
    transform: scale(1);
  }
}

.detail-skeleton {
  height: 12px;
  margin-bottom: 11px;
  border-radius: 4px;
  background: linear-gradient(90deg, rgba(226, 223, 213, 0.45) 25%, rgba(226, 223, 213, 0.9) 37%, rgba(226, 223, 213, 0.45) 63%);
  background-size: 400% 100%;
  animation: detail-shimmer 1.4s ease infinite;

  &--lead {
    width: 82%;
    height: 16px;
  }

  &--short {
    width: 58%;
  }
}

@keyframes detail-shimmer {
  0% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0 50%;
  }
}

.detail-loading-hint {
  margin-top: 13px;
  color: var(--fw-text-3, #8a938c);
  font-size: 11.5px;
}

.detail-error {
  margin-top: 22px;
  padding: 20px;
  border: 1px dashed var(--fw-border, #e2dfd5);
  border-radius: 10px;
  background: #fff;
  text-align: center;

  p {
    margin: 0 0 12px;
    color: var(--fw-text-2, #5c675f);
    font-size: 13px;
  }
}

.detail-retry {
  padding: 7px 18px;
  border: 1px solid var(--fw-accent, #0f6b4f);
  border-radius: 999px;
  background: transparent;
  color: var(--fw-accent, #0f6b4f);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.18s ease;

  &:hover {
    background: var(--fw-accent, #0f6b4f);
    color: #fff;
  }
}

.detail-source {
  margin: 18px 0 0;
  color: var(--fw-text-3, #8a938c);
  font-size: 11px;
}

@media (max-width: 860px) {
  .attraction-detail {
    padding: 24px 20px 22px;
    border-radius: 14px;
  }

  .detail-columns {
    grid-template-columns: minmax(0, 1fr);
    gap: 22px;
  }

  .detail-aside {
    padding: 15px 15px 13px;
  }

  .detail-title {
    font-size: 24px;
  }

  .detail-gallery__hero {
    height: 205px;
  }

  .detail-gallery__thumbs img {
    height: 118px;
  }

  .detail-overview {
    margin-top: 16px;
    padding: 13px 15px;
    font-size: 14px;
    line-height: 1.85;
  }

  .detail-history {
    font-size: 13.5px;
    line-height: 1.9;
  }

  .detail-head {
    padding-right: 30px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .attraction-detail {
    animation: none;
  }

  .detail-skeleton,
  .detail-loading-dot {
    animation: none;
  }
}
</style>
