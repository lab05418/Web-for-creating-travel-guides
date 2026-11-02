<template>
  <nav class="navbar navbar-toggleable-md fixed-top navbar-transparent landing-navbar">
    <div class="container">
      <div class="navbar-translate">
        <button
          class="navbar-toggler navbar-toggler-right navbar-burger landing-burger"
          type="button"
          aria-label="Toggle navigation"
        >
          <span class="navbar-toggler-bar"></span>
          <span class="navbar-toggler-bar"></span>
          <span class="navbar-toggler-bar"></span>
        </button>
        <button class="navbar-brand landing-brand" type="button" @click="handleBrandClick">Farway</button>
      </div>
      <div class="navbar-collapse landing-navbar-collapse" id="navbarToggler">
        <ul class="navbar-nav ml-auto landing-nav">
          <li class="nav-item">
            <!-- <button class="nav-link landing-nav-btn fog-toggle" type="button" :aria-pressed="fogEnabled" @click="toggleFog">
              {{ fogEnabled ? t('home.nav.fogOn') : t('home.nav.fogOff') }}
            </button> -->
          </li>
          <li class="nav-item landing-lang-item">
            <a-select v-model:value="locale" class="lang-select-nav" size="small" :aria-label="t('app.language.label')">
              <a-select-option value="zh-CN">{{ t('app.language.zh') }}</a-select-option>
              <a-select-option value="ja-JP">{{ t('app.language.ja') }}</a-select-option>
              <a-select-option value="en-US">{{ t('app.language.en') }}</a-select-option>
            </a-select>
          </li>
          <li class="nav-item">
            <button
              type="button"
              class="nav-link landing-nav-btn settings-btn"
              :title="t('settings.open')"
              :aria-label="t('settings.open')"
              @click="openSettingsDialog"
            >
              <svg width="25px" height="25px" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M600.704 64a32 32 0 0 1 30.464 22.208l35.2 109.376c14.784 7.232 28.928 15.36 42.432 24.512l112.384-24.192a32 32 0 0 1 34.432 15.36L944.32 364.8a32 32 0 0 1-4.032 37.504l-77.12 85.12a357.12 357.12 0 0 1 0 49.024l77.12 85.248a32 32 0 0 1 4.032 37.504l-88.704 153.6a32 32 0 0 1-34.432 15.296L708.8 803.904c-13.44 9.088-27.648 17.28-42.368 24.512l-35.264 109.376A32 32 0 0 1 600.704 960H423.296a32 32 0 0 1-30.464-22.208L357.696 828.48a351.616 351.616 0 0 1-42.56-24.64l-112.32 24.256a32 32 0 0 1-34.432-15.36L79.68 659.2a32 32 0 0 1 4.032-37.504l77.12-85.248a357.12 357.12 0 0 1 0-48.896l-77.12-85.248A32 32 0 0 1 79.68 364.8l88.704-153.6a32 32 0 0 1 34.432-15.296l112.32 24.256c13.568-9.152 27.776-17.408 42.56-24.64l35.2-109.312A32 32 0 0 1 423.232 64H600.64zm-23.424 64H446.72l-36.352 113.088-24.512 11.968a294.113 294.113 0 0 0-34.816 20.096l-22.656 15.36-116.224-25.088-65.28 113.152 79.68 88.192-1.92 27.136a293.12 293.12 0 0 0 0 40.192l1.92 27.136-79.808 88.192 65.344 113.152 116.224-25.024 22.656 15.296a294.113 294.113 0 0 0 34.816 20.096l24.512 11.968L446.72 896h130.688l36.48-113.152 24.448-11.904a288.282 288.282 0 0 0 34.752-20.096l22.592-15.296 116.288 25.024 65.28-113.152-79.744-88.192 1.92-27.136a293.12 293.12 0 0 0 0-40.256l-1.92-27.136 79.808-88.128-65.344-113.152-116.288 24.96-22.592-15.232a287.616 287.616 0 0 0-34.752-20.096l-24.448-11.904L577.344 128zM512 320a192 192 0 1 1 0 384 192 192 0 0 1 0-384zm0 64a128 128 0 1 0 0 256 128 128 0 0 0 0-256z"/></svg>
            </button>
          </li>
          <li class="nav-item">
            <button type="button" class="btn btn-danger btn-round landing-cta" @click="handleCtaClick">
              {{ t('home.nav.cta') }}
            </button>
          </li>
        </ul>
      </div>
    </div>
    <a-modal
      v-model:open="settingsVisible"
      class="settings-modal"
      :title="t('settings.title')"
      :width="820"
      :confirm-loading="settingsSaving"
      :ok-text="t('settings.saveApply')"
      :cancel-text="t('settings.cancel')"
      :ok-button-props="{ disabled: settingsReadonly }"
      @ok="saveSettingsNow"
    >
      <a-spin :spinning="settingsLoading">
        <a-alert
          v-if="settingsReadonly"
          type="warning"
          show-icon
          :message="t('settings.publicReadonly')"
          style="margin-bottom: 12px"
        />
        <section class="runtime-settings-panel">

          <a-form layout="vertical" class="runtime-settings-form">
            <div class="runtime-settings-grid">
              <a-form-item>
                <template #label>
                  <span class="field-label">{{ t('settings.labels.apiBaseUrl') }}</span>
                </template>
                <a-input
                  v-model:value="settingsForm.api_base_url"
                  :placeholder="t('settings.placeholders.apiBaseUrl')"
                  allow-clear
                />
              </a-form-item>

              <a-form-item>
                <template #label>
                  <span class="field-label">{{ t('settings.labels.amapJsKey') }}</span>
                </template>
                <a-input-password v-model:value="settingsForm.vite_amap_web_js_key" allow-clear />
              </a-form-item>

              <a-form-item>
                <template #label>
                  <span class="field-label">{{ t('settings.labels.amapWebKey') }}</span>
                </template>
                <a-input-password v-model:value="settingsForm.vite_amap_web_key" allow-clear />
              </a-form-item>

              <a-form-item>
                <template #label>
                  <span class="field-label">{{ t('settings.labels.amapSecurityCode') }}</span>
                </template>
                <a-input-password v-model:value="settingsForm.vite_amap_security_js_code" allow-clear />
              </a-form-item>

              <a-form-item>
                <template #label>
                  <span class="field-label">{{ t('settings.labels.openaiBaseUrl') }}</span>
                </template>
                <a-input
                  v-model:value="settingsForm.openai_base_url"
                  :placeholder="t('settings.placeholders.openaiBaseUrl')"
                  allow-clear
                />
              </a-form-item>

              <a-form-item>
                <template #label>
                  <span class="field-label">{{ t('settings.labels.openaiModel') }}</span>
                </template>
                <a-input
                  v-model:value="settingsForm.openai_model"
                  :placeholder="t('settings.placeholders.openaiModel')"
                  allow-clear
                />
              </a-form-item>

              <a-form-item>
                <template #label>
                  <span class="field-label">{{ t('settings.labels.openaiApiKey') }}</span>
                </template>
                <a-input-password v-model:value="settingsForm.openai_api_key" allow-clear />
              </a-form-item>
            </div>

            <a-form-item class="runtime-settings-full">
              <template #label>
                <span class="field-label">{{ t('settings.labels.xhsCookie') }}</span>
              </template>
              <a-textarea
                v-model:value="settingsForm.xhs_cookie"
                :rows="4"
                :placeholder="t('settings.placeholders.xhsCookie')"
                allow-clear
              />
              <div v-if="xhsSession" class="xhs-session-status">
                <span>{{ t('settings.xhsSessionLabel') }}</span>
                <strong :class="`xhs-status-${xhsSession.status || 'unknown'}`">{{ xhsSessionText }}</strong>
                <span v-if="xhsSession.last_ok_at">{{ t('settings.xhsSessionLastOk') }}: {{ formatSessionTime(xhsSession.last_ok_at) }}</span>
              </div>
              <div class="field-hint">{{ t('settings.xhsCookieEncrypted') }}</div>
            </a-form-item>
          </a-form>
        </section>
      </a-spin>
    </a-modal>
  </nav>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useI18n } from 'vue-i18n'
import type { RuntimeSettings, XhsSessionStatus } from '@/types'
import { getRuntimeCapabilities, getRuntimeSettings, saveRuntimeSettings } from '@/services/api'

const { t, locale } = useI18n()
const settingsVisible = ref(false)
const settingsLoading = ref(false)
const settingsSaving = ref(false)
const settingsReadonly = ref(false)
const xhsSession = ref<XhsSessionStatus | null>(null)
const xhsSessionText = computed(() => {
  const status = String(xhsSession.value?.status || 'unknown')
  const key = `settings.xhsSession.${status}`
  const translated = t(key)
  return translated === key ? t('settings.xhsSession.unknown') : translated
})
const formatSessionTime = (value?: string | null) => {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}
const settingsForm = reactive<RuntimeSettings>({
  api_base_url: '',
  vite_amap_web_key: '',
  vite_amap_web_js_key: '',
  vite_amap_security_js_code: '',
  xhs_cookie: '',
  openai_api_key: '',
  openai_base_url: '',
  openai_model: '',
})

const emit = defineEmits<{
  (e: 'brand-click'): void
  (e: 'cta-click'): void
}>()

const handleBrandClick = () => {
  emit('brand-click')
}

const handleCtaClick = () => {
  emit('cta-click')
}

const applyRuntimeSettings = (settings: RuntimeSettings) => {
  settingsForm.api_base_url = settings.api_base_url || ''
  settingsForm.vite_amap_web_key = settings.vite_amap_web_key || ''
  settingsForm.vite_amap_web_js_key = settings.vite_amap_web_js_key || ''
  settingsForm.vite_amap_security_js_code = settings.vite_amap_security_js_code || ''
  settingsForm.xhs_cookie = settings.xhs_cookie || ''
  xhsSession.value = settings.xhs_session || null
  settingsForm.openai_api_key = settings.openai_api_key || ''
  settingsForm.openai_base_url = settings.openai_base_url || ''
  settingsForm.openai_model = settings.openai_model || ''
}

const openSettingsDialog = async () => {
  settingsVisible.value = true
  settingsLoading.value = true
  try {
    const [settings, capabilities] = await Promise.all([
      getRuntimeSettings(),
      getRuntimeCapabilities(),
    ])
    settingsReadonly.value = !capabilities.settings_writable
    applyRuntimeSettings(settings)
  } catch (error: any) {
    message.error(error?.message || t('settings.messages.loadFailed'))
  } finally {
    settingsLoading.value = false
  }
}

const saveSettingsNow = async () => {
  if (settingsReadonly.value) {
    message.warning(t('settings.publicReadonly'))
    return
  }
  settingsSaving.value = true
  try {
    const payload: RuntimeSettings = {
      api_base_url: settingsForm.api_base_url,
      vite_amap_web_key: settingsForm.vite_amap_web_key,
      vite_amap_web_js_key: settingsForm.vite_amap_web_js_key,
      vite_amap_security_js_code: settingsForm.vite_amap_security_js_code,
      xhs_cookie: settingsForm.xhs_cookie,
      openai_api_key: settingsForm.openai_api_key,
      openai_base_url: settingsForm.openai_base_url,
      openai_model: settingsForm.openai_model,
    }
    const saved = await saveRuntimeSettings(payload)
    applyRuntimeSettings(saved)
    message.success(t('settings.messages.saved'))
    settingsVisible.value = false
  } catch (error: any) {
    message.error(error?.message || t('settings.messages.saveFailed'))
  } finally {
    settingsSaving.value = false
  }
}
</script>

<style scoped>
.landing-navbar {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  width: 100% !important;
  z-index: 1030 !important;
  min-height: 70px;
  padding: 0 !important;
  background: transparent !important;
  background-color: transparent !important;
  background-image: none !important;
  box-shadow: none !important;
  border: none !important;
  border-bottom: 1px solid transparent !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  transition: background 0.3s;
}

.landing-navbar:not(.navbar-transparent) {
  background: transparent !important;
  background-color: transparent !important;
  background-image: none !important;
  border-color: transparent !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
}

.landing-navbar.navbar-transparent {
  padding-top: 0 !important;
  background: transparent !important;
  background-color: transparent !important;
  background-image: none !important;
  box-shadow: none !important;
}

.landing-navbar *,
.landing-navbar::before,
.landing-navbar::after {
  box-sizing: border-box;
}

.landing-navbar .container {
  width: 100% !important;
  max-width: 100vw !important;
  min-height: 70px;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  padding-left: 20px;
  padding-right: 20px;
  box-sizing: border-box !important;
}

.landing-navbar .navbar-translate {
  display: flex !important;
  align-items: center !important;
  min-height: 70px;
  flex: 0 0 auto;
}

.landing-navbar .navbar-brand {
  margin: 0 !important;
  padding: 0 !important;
  line-height: 1 !important;
}

.landing-burger {
  display: none !important;
}

.landing-brand {
  background: transparent !important;
  border: 0;
  color: #1B2420 !important;
  font-weight: 700 !important;
  letter-spacing: 0.12em !important;
  text-transform: uppercase;
  font-size: 13px !important;
  cursor: pointer;
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.landing-navbar-collapse {
  display: flex !important;
  justify-content: flex-end;
  align-items: center;
  flex: 1;
  position: static !important;
  transform: none !important;
  width: auto !important;
  height: auto !important;
  background: transparent !important;
  border: 0 !important;
  padding: 0 !important;
  overflow: visible !important;
}

.landing-navbar-collapse::before,
.landing-navbar-collapse::after {
  display: none !important;
  content: none !important;
  background: transparent !important;
}

.landing-nav {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 0 auto !important;
  padding: 0;
  list-style: none;
}

.landing-nav .nav-item {
  margin: 0;
  padding: 0;
  display: inline-flex;
  align-items: center;
}

.landing-nav .nav-item .nav-link {
  margin: 0 !important;
  padding: 0 !important;
  line-height: 1 !important;
  opacity: 1 !important;
}

.landing-nav-btn {
  border: 1.2px solid #DDD9CD;
  background: #FFFFFF;
  color: #1B2420;
  border-radius: 999px;
  padding: 0 12px;
  min-height: 34px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  text-transform: uppercase;
}

.settings-btn {
  text-transform: none;
  border: none !important;
  background: none !important;
}

.fog-toggle[aria-pressed='true'] {
  border-color: rgba(215, 110, 66, 0.55);
  background: rgba(215, 110, 66, 0.2);
  color: #ffe3d6;
}

.landing-lang-item {
  display: flex;
  align-items: center;
}

.lang-select-nav {
  width: 110px;
}

.lang-select-nav :deep(.ant-select-selector) {
  height: 34px !important;
  padding: 0 12px !important;
  border: 1.2px solid #DDD9CD !important;
  background: #FFFFFF !important;
  border-radius: 999px !important;
  display: flex !important;
  align-items: center !important;
}

.lang-select-nav :deep(.ant-select-selection-item) {
  line-height: 32px !important;
  font-size: 12px !important;
}

.lang-select-nav :deep(.ant-select-selection-item),
.lang-select-nav :deep(.ant-select-arrow) {
  color: #1B2420 !important;
}

.landing-cta {
  min-height: 32px;
  padding: 0 14px !important;
  font-size: 12px !important;
  border: none !important;
  letter-spacing: 0.06em;
  display: inline-flex !important;
  align-items: center;
  justify-content: center;
  margin: 0 !important;
}

.landing-navbar .btn {
  margin: 0 !important;
}

@media (max-width: 991px) {
  .landing-navbar {
    min-height: 64px;
  }

  .landing-navbar .container {
    padding-left: 14px;
    padding-right: 14px;
    min-height: 64px;
  }

  .landing-navbar .navbar-translate {
    min-height: 64px;
  }

  .lang-select-nav {
    width: 92px;
  }

  .landing-cta {
    min-height: 34px;
    padding: 0 10px !important;
  }

  .landing-nav {
    gap: 6px;
  }
}

@media (max-width: 520px) {
  .landing-navbar .container {
    padding-left: 8px;
    padding-right: 8px;
  }

  .landing-brand {
    font-size: 10px !important;
    letter-spacing: 0.05em !important;
    max-width: 70px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .landing-nav {
    gap: 3px !important;
  }

  .lang-select-nav {
    width: 68px !important;
  }

  .lang-select-nav :deep(.ant-select-selector) {
    padding: 0 4px !important;
  }

  .landing-cta {
    padding: 0 8px !important;
    font-size: 10px !important;
    min-height: 30px !important;
    margin-right: 0 !important;
  }
}

@media (max-width: 400px) {
  .landing-nav .nav-item:first-child {
    display: none !important;
  }

  .lang-select-nav {
    width: 62px !important;
  }
}

.runtime-settings-form :deep(.ant-form-item) {
  margin-bottom: 12px;
}

/* Farway 浅色导航 */
.landing-navbar {
  background: rgba(246, 245, 240, 0.86) !important;
  border-bottom: 1px solid #E2DFD5 !important;
  backdrop-filter: blur(12px) !important;
  -webkit-backdrop-filter: blur(12px) !important;
}

.landing-brand {
  color: #1B2420 !important;
}

.landing-nav-btn {
  border-color: #DDD9CD !important;
  background: #FFFFFF !important;
  color: #1B2420 !important;
}

.lang-select-nav :deep(.ant-select-selector) {
  background: #FFFFFF !important;
  border-color: #DDD9CD !important;
}

.lang-select-nav :deep(.ant-select-selection-item),
.lang-select-nav :deep(.ant-select-arrow) {
  color: #1B2420 !important;
}

.xhs-session-status {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 12px;
  margin-top: 6px;
  color: #5C675F;
  font-size: 12px;
}

.xhs-session-status strong {
  font-weight: 700;
}

.xhs-status-active {
  color: #0F6B4F;
}

.xhs-status-degraded {
  color: #A46A00;
}

.xhs-status-expired,
.xhs-status-disabled {
  color: #A83B2B;
}

.xhs-status-needs_login,
.xhs-status-unknown {
  color: #6B756E;
}
</style>
