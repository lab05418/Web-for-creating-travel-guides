<template>
  <div class="result-container">
    <div class="lower-shade"></div>

    <NavBar @brand-click="goBack" @cta-click="goBack" />

    <main class="result-main">
      <div v-if="tripPlan" class="content-wrapper" :inert="discoverUpdating || undefined">
        <div class="top-switch-nav">
          <div class="top-switch-menu-wrap">
            <a-menu class="top-switch-menu" mode="horizontal" :selected-keys="[activeSection]" @click="scrollToSection">
              <a-menu-item key="overview">
                <span>{{ t('result.side.overview') }}</span>
              </a-menu-item>
              <a-menu-item key="discover">
                <span>{{ t('result.side.discover') }}</span>
              </a-menu-item>
              <a-menu-item key="budget" v-if="tripPlan.budget">
                <span>{{ t('result.side.budget') }}</span>
              </a-menu-item>
              <a-menu-item key="map">
                <span>{{ t('result.side.map') }}</span>
              </a-menu-item>
              <a-menu-item key="days">
                <span>{{ t('result.side.days') }}</span>
              </a-menu-item>

              <a-menu-item key="weather" v-if="tripPlan.weather_info && tripPlan.weather_info.length > 0">
                <span>{{ t('result.side.weather') }}</span>
              </a-menu-item>
            </a-menu>
          </div>

          <div class="top-switch-actions">
            <a-space size="middle" wrap>
              <a-button type="default" :loading="mapRefreshing" @click="refreshMap()">
                {{ t('result.refreshMap') }}
              </a-button>
              <a-button v-if="!editMode" @click="toggleEditMode" type="default">
                {{ t('result.editTrip') }}
              </a-button>
              <a-button v-else @click="saveChanges" type="primary">
                {{ t('result.saveChanges') }}
              </a-button>
              <a-button v-if="editMode" @click="cancelEdit" type="default">
                {{ t('result.cancelEdit') }}
              </a-button>

              <a-button v-if="!editMode" type="default" @click="exportAsImage">
                {{ t('result.exportImage') }}
              </a-button>
            </a-space>
          </div>
        </div>

      <!-- 主内容区 -->
        <a-card
          v-show="activeSection === 'overview'"
          id="overview"
          :bordered="false"
          class="overview-card section-shellless"
        >
          <div v-if="overviewAttractions.length > 0" class="overview-grid">
            <OverviewAttractionCard
              v-for="(item, index) in overviewAttractions"
              :key="`${item.dayArrayIndex}-${item.order}-${item.name}`"
              :item="item"
              :image-src="getAttractionImage(item.name, index)"
              @image-error="handleImageError"
              @mouseenter="prefetchOverviewGuide(item)"
              @open-detail="openOverviewDetail(item)"
            />
          </div>
          <a-empty v-else :description="t('common.noData')" />
          <div class="overview-meta">
            <span class="overview-meta-item" style="color: #0F6B4F; font-weight: 700;">
              {{ t('result.dateRange', { start: tripPlan.start_date, end: tripPlan.end_date }) }}
            </span>
            <span v-if="planId" class="overview-meta-item">
              Plan ID: {{ planId }}
            </span>
            <span v-if="tripFormMeta.origin" class="overview-meta-item">
              {{ t('home.originLabel') }}: {{ tripFormMeta.origin }}<template v-if="tripFormMeta.intercity_transportation"> · {{ tripFormMeta.intercity_transportation }}</template><template v-if="interCitySeatLabel"> · {{ interCitySeatLabel }}</template>
            </span>
            <span v-if="tripPlan.overall_suggestions" class="overview-meta-item">
              {{ tripPlan.overall_suggestions }}
            </span>
          </div>
          <div class="overview-discover-entry">
            <div class="overview-discover-copy">
              <p class="overview-discover-title">{{ t('result.discover.entryTitle') }}</p>
              <p class="overview-discover-desc">{{ t('result.discover.entryDesc') }}</p>
            </div>
            <a-button type="primary" class="overview-discover-btn" @click="openDiscoverPage">
              {{ t('result.discover.entryAction') }}
            </a-button>
          </div>
          <ImportantReminders
            v-if="overviewReminders.length"
            :items="overviewReminders"
            :heading="t('result.reminders.overviewTitle')"
            class="overview-reminders"
          />
          <OverviewAttractionDetail
            v-if="overviewDetailItem"
            :item="overviewDetailItem"
            :images="overviewDetailImages"
            :guide="overviewGuide"
            :loading="overviewGuideLoading"
            :error="overviewGuideError"
            @close="closeOverviewDetail"
            @retry="retryOverviewDetail"
          />
        </a-card>

        <!-- 热门景点发现页 -->
        <a-card
          v-show="activeSection === 'discover'"
          id="discover"
          :bordered="false"
          class="discover-page section-shellless"
          :aria-busy="discoverUpdating"
        >
          <div class="discover-head">
            <button type="button" class="discover-back" @click="activeSection = 'overview'">
              ← {{ t('result.discover.back') }}
            </button>
            <div class="discover-heading">
              <h2>{{ t('result.discover.title') }}</h2>
              <p>{{ t('result.discover.subtitle', { city: tripPlan.city }) }}</p>
            </div>
            <a-button :loading="popularLoading" :disabled="discoverUpdating" @click="loadPopularAttractions(true)">
              {{ t('result.discover.refresh') }}
            </a-button>
          </div>

          <div class="discover-toolbar">
            <span>{{ t('result.discover.addToDay') }}</span>
            <a-select
              v-model:value="discoverAddDay"
              :options="discoverDayOptions"
              size="small"
              class="discover-day-select"
              :disabled="discoverUpdating"
            />
          </div>

          <a-spin :spinning="popularLoading">
            <div v-if="popularError" class="discover-state">
              <p>{{ popularError }}</p>
              <a-button :disabled="discoverUpdating" @click="loadPopularAttractions(true)">
                {{ t('result.discover.retry') }}
              </a-button>
            </div>
            <a-empty
              v-else-if="!popularAttractions.length && !popularLoading"
              :description="t('result.discover.empty')"
            />
            <div v-else class="discover-grid">
              <article
                v-for="(item, index) in popularAttractions"
                :key="item.id || item.name"
                class="discover-card"
              >
                <div class="discover-card-media">
                  <img
                    :src="toDisplayPhotoUrl(item.image_url) || getAttractionImage(item.name, index)"
                    :alt="item.name"
                    loading="lazy"
                    decoding="async"
                    referrerpolicy="no-referrer"
                    @error="handleImageError"
                  />
                  <span v-if="item.rating" class="discover-rating">★ {{ item.rating }}</span>
                  <span class="discover-category">{{ item.category }}</span>
                </div>
                <div class="discover-card-body">
                  <h3>{{ item.name }}</h3>
                  <p class="discover-card-desc">{{ item.description }}</p>
                  <p class="discover-card-address">{{ item.address }}</p>
                  <div class="discover-card-actions">
                    <a-button size="small" :disabled="discoverUpdating" @click="openDiscoverDetail(item)">
                      {{ t('result.discover.detail') }}
                    </a-button>
                    <a-button
                      type="primary"
                      size="small"
                      :loading="discoverAddingId === item.id"
                      :disabled="discoverUpdating"
                      @click="addPopularAttraction(item)"
                    >
                      {{ t('result.discover.add') }}
                    </a-button>
                  </div>
                </div>
              </article>
            </div>
          </a-spin>

          <div
            v-if="discoverDetailItem && discoverDetail"
            class="discover-detail-overlay"
            @click.self="closeDiscoverDetail"
          >
            <div class="discover-detail-panel">
              <OverviewAttractionDetail
                :item="discoverDetailItem"
                :images="discoverDetailImages"
                :guide="discoverGuide"
                :loading="discoverGuideLoading"
                :error="discoverGuideError"
                :day-label="t('result.discover.detailLabel')"
                :price-known="typeof discoverDetail.ticket_price === 'number'"
                @close="closeDiscoverDetail"
                @retry="retryDiscoverDetail"
              />
              <div class="discover-detail-actions">
                <span>{{ t('result.discover.addToDay') }}</span>
                <a-select
                  v-model:value="discoverAddDay"
                  :options="discoverDayOptions"
                  size="small"
                  class="discover-day-select"
                  :disabled="discoverUpdating"
                />
                <a-button
                  type="primary"
                  :loading="discoverAddingId === discoverDetail.id"
                  :disabled="discoverUpdating"
                  @click="addPopularAttraction(discoverDetail)"
                >
                  {{ t('result.discover.add') }}
                </a-button>
              </div>
            </div>
          </div>
        </a-card>

        <!-- 顶部信息区:预算/地图 -->
        <div class="top-info-section" v-show="['budget', 'map'].includes(activeSection)">
          <div class="left-info" v-show="activeSection === 'budget'">
            <a-card
              v-show="activeSection === 'budget' && !!tripPlan.budget"
              id="budget"
              v-if="tripPlan.budget"
              :bordered="false"
              class="budget-card section-shellless"
            >
              <div class="budget-detail-panel">
                <div class="budget-toolbar">
                  <div class="budget-toolbar-item">
                    <span class="budget-toolbar-label">{{ t('result.budget.filterLabel') }}</span>
                    <a-select v-model:value="budgetFilterType" size="small" class="budget-select">
                      <a-select-option value="all">{{ t('result.budget.filterAll') }}</a-select-option>
                      <a-select-option value="attraction">{{ t('result.budget.attraction') }}</a-select-option>
                      <a-select-option value="hotel">{{ t('result.budget.hotel') }}</a-select-option>
                      <a-select-option value="meal">{{ t('result.budget.meal') }}</a-select-option>
                      <a-select-option value="transport">{{ t('result.budget.transport') }}</a-select-option>
                    </a-select>
                  </div>
                  <div class="budget-toolbar-item">
                    <span class="budget-toolbar-label">{{ t('result.budget.dayFilterLabel') }}</span>
                    <a-select v-model:value="budgetFilterDay" size="small" class="budget-select">
                      <a-select-option value="all">{{ t('result.budget.allDays') }}</a-select-option>
                      <a-select-option
                        v-for="(_, dayIndex) in tripPlan.days"
                        :key="`budget-day-${dayIndex}`"
                        :value="dayIndex"
                      >
                        {{ t('common.dayNumber', { day: dayIndex + 1 }) }}
                      </a-select-option>
                    </a-select>
                  </div>
                  <div class="budget-toolbar-item">
                    <span class="budget-toolbar-label">{{ t('result.budget.sortLabel') }}</span>
                    <a-select v-model:value="budgetSortMode" size="small" class="budget-select">
                      <a-select-option value="playOrder">{{ t('result.budget.sortPlayOrder') }}</a-select-option>
                      <a-select-option value="amountDesc">{{ t('result.budget.sortAmountDesc') }}</a-select-option>
                      <a-select-option value="amountAsc">{{ t('result.budget.sortAmountAsc') }}</a-select-option>
                      <a-select-option value="dayAsc">{{ t('result.budget.sortDayAsc') }}</a-select-option>
                      <a-select-option value="dayDesc">{{ t('result.budget.sortDayDesc') }}</a-select-option>
                      <a-select-option value="custom">{{ t('result.budget.sortCustom') }}</a-select-option>
                    </a-select>
                  </div>
                </div>

                <div class="budget-detail-reference">{{ t('result.budget.referenceNote') }}</div>

                <div class="budget-result-meta">
                  <span class="budget-result-day">{{ budgetFilterDayLabel }}</span>
                  <span class="budget-result-count">{{ t('result.budget.itemCount', { count: filteredBudgetItems.length }) }}</span>
                  <span class="budget-result-total">{{ t('result.budget.subtotal') }} ¥{{ formatBudgetAmount(filteredBudgetTotal) }}</span>
                  <a-button
                    v-if="budgetSortMode === 'custom'"
                    type="link"
                    size="small"
                    class="budget-reset-order"
                    @click="resetBudgetOrder"
                  >
                    {{ t('result.budget.resetOrder') }}
                  </a-button>
                </div>

                <div v-if="filteredBudgetItems.length > 0" class="budget-detail-list">
                  <div class="budget-detail-row budget-detail-header">
                    <span class="budget-detail-type">{{ t('result.budget.detailType') }}</span>
                    <span class="budget-detail-day">{{ t('result.budget.detailDay') }}</span>
                    <span class="budget-detail-name">{{ t('result.budget.detailName') }}</span>
                    <span class="budget-detail-amount">{{ t('result.budget.detailAmount') }}</span>
                    <span class="budget-detail-action">{{ t('result.budget.detailAction') }}</span>
                  </div>
                  <div
                    v-for="item in filteredBudgetItems"
                    :key="item.id"
                    class="budget-detail-row"
                  >
                    <span class="budget-detail-type">{{ getBudgetTypeLabel(item.type) }}</span>
                    <span class="budget-detail-day">
                      {{ item.dayNumber ? t('common.dayNumber', { day: item.dayNumber }) : '--' }}
                    </span>
                    <span class="budget-detail-name">{{ item.name }}</span>
                    <span class="budget-detail-amount">
                      <span v-if="editingBudgetId !== item.id">¥{{ formatBudgetAmount(item.amount) }}</span>
                      <span v-else class="budget-inline-edit">
                        <span class="budget-inline-currency">¥</span>
                        <a-input-number
                          v-model:value="budgetEditDraft"
                          class="budget-inline-input"
                          :min="0"
                          :precision="2"
                          :step="10"
                          size="small"
                          :data-budget-input="item.id"
                          @press-enter="saveBudgetEdit(item)"
                        />
                      </span>
                    </span>
                    <span class="budget-action-wrap">
                      <template v-if="editingBudgetId === item.id">
                        <button
                          type="button"
                          class="budget-icon-btn budget-save-btn"
                          :title="t('result.budget.saveAmount')"
                          @click="saveBudgetEdit(item)"
                        >
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M5 12.5l4.2 4.2L19 7" />
                          </svg>
                        </button>
                        <button
                          type="button"
                          class="budget-icon-btn budget-cancel-btn"
                          :title="t('result.budget.cancelEdit')"
                          @click="cancelBudgetEdit"
                        >
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                            <path stroke-linecap="round" d="M6 6l12 12M18 6L6 18" />
                          </svg>
                        </button>
                      </template>
                      <template v-else>
                        <button
                          type="button"
                          class="budget-icon-btn budget-move-btn"
                          :title="t('result.budget.moveUp')"
                          :disabled="!canMoveBudgetItem(item, -1)"
                          @click="moveBudgetItem(item, -1)"
                        >
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M6 14l6-6 6 6" />
                          </svg>
                        </button>
                        <button
                          type="button"
                          class="budget-icon-btn budget-move-btn"
                          :title="t('result.budget.moveDown')"
                          :disabled="!canMoveBudgetItem(item, 1)"
                          @click="moveBudgetItem(item, 1)"
                        >
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M6 10l6 6 6-6" />
                          </svg>
                        </button>
                        <button
                          type="button"
                          class="budget-icon-btn budget-edit-btn"
                          :title="t('result.budget.editPrice')"
                          @click="startBudgetEdit(item)"
                        >
                          <svg fill="currentColor" width="20px" height="20px" viewBox="0 0 256.00098 256.00098" id="Flat" xmlns="http://www.w3.org/2000/svg">
                            <path d="M216.001,203.833h-76l27.91015-27.90967.00684-.00635.00635-.00683,56.563-56.5625a28.03348,28.03348,0,0,0-.001-39.59766L179.23145,34.49512a28.03347,28.03347,0,0,0-39.59766,0L83.07471,91.0542l-.01026.00928-.00927.01025L26.49609,147.63281a28.03171,28.03171,0,0,0,0,39.59766L63.585,224.31836a12.00286,12.00286,0,0,0,8.48535,3.51465H216.001a12,12,0,0,0,0-24ZM156.60449,51.46582a4.00207,4.00207,0,0,1,5.65625,0L207.51562,96.7207a4.005,4.005,0,0,1,0,5.65723l-48.083,48.083L108.521,99.54932ZM106.05957,203.833H77.041L43.4668,170.25977a4.00385,4.00385,0,0,1,0-5.65625L91.55029,116.52l50.91114,50.91113Z"/>
                          </svg>
                        </button>
                        <button
                          type="button"
                          class="budget-icon-btn budget-delete-btn"
                          :title="t('common.delete')"
                          @click="deleteBudgetItem(item)"
                        >
                          <svg fill="currentColor" width="21px" height="21px" viewBox="0 0 256 256" id="Flat" xmlns="http://www.w3.org/2000/svg">
                            <path d="M215.99609,48H180V36A28.03146,28.03146,0,0,0,152,8H104A28.03146,28.03146,0,0,0,76,36V48H39.99609a12,12,0,0,0,0,24h4V208a20.0226,20.0226,0,0,0,20,20h128a20.0226,20.0226,0,0,0,20-20V72h4a12,12,0,0,0,0-24ZM100,36a4.00458,4.00458,0,0,1,4-4h48a4.00458,4.00458,0,0,1,4,4V48H100Zm87.99609,168h-120V72h120ZM116,104v64a12,12,0,0,1-24,0V104a12,12,0,0,1,24,0Zm48,0v64a12,12,0,0,1-24,0V104a12,12,0,0,1,24,0Z"/>
                          </svg>
                        </button>
                      </template>
                    </span>
                  </div>
                </div>
                <a-empty v-else :description="t('result.budget.noDetails')" />
              </div>
            </a-card>
          </div>

          <div class="right-budget-summary" v-show="activeSection === 'budget' && !!tripPlan.budget">
            <div class="budget-summary-panel">
              <div class="budget-summary-title">{{ t('result.budget.title') }}</div>
              <div class="budget-reference-note">{{ t('result.budget.referenceNote') }}</div>
              <div class="budget-summary-total-label">{{ budgetTotalLabel }}</div>
              <div class="budget-summary-total-wrap">
                <span class="budget-summary-currency">¥</span>
                <span class="budget-summary-total-value">{{ formatBudgetAmount(tripPlan.budget?.total ?? 0) }}</span>
              </div>
              <div v-if="budgetLimit" class="budget-limit-bar" :class="{ over: budgetOverAmount > 0 }">
                <span class="budget-limit-label">{{ t('result.budget.limitLabel') }} ¥{{ formatBudgetAmount(budgetLimit) }}</span>
                <span class="budget-limit-status">
                  {{ budgetOverAmount > 0
                    ? t('result.budget.overBudget', { amount: formatBudgetAmount(budgetOverAmount) })
                    : t('result.budget.withinBudget') }}
                </span>
              </div>
              <div class="budget-summary-sub-grid">
                <div class="budget-summary-sub-item">
                  <div class="budget-summary-sub-value">¥{{ formatBudgetAmount(tripPlan.budget?.total_attractions ?? 0) }}</div>
                  <div class="budget-summary-sub-label">{{ t('result.budget.attraction') }}</div>
                </div>
                <div class="budget-summary-sub-item">
                  <div class="budget-summary-sub-value">¥{{ formatBudgetAmount(tripPlan.budget?.total_hotels ?? 0) }}</div>
                  <div class="budget-summary-sub-label">{{ t('result.budget.hotel') }}</div>
                </div>
                <div class="budget-summary-sub-item">
                  <div class="budget-summary-sub-value">¥{{ formatBudgetAmount(tripPlan.budget?.total_meals ?? 0) }}</div>
                  <div class="budget-summary-sub-label">{{ t('result.budget.meal') }}</div>
                </div>
                <div class="budget-summary-sub-item">
                  <div class="budget-summary-sub-value">¥{{ formatBudgetAmount(tripPlan.budget?.total_transportation ?? 0) }}</div>
                  <div class="budget-summary-sub-label">{{ t('result.budget.transport') }}</div>
                </div>
                <div v-if="interCityTotal > 0" class="budget-summary-sub-item budget-summary-sub-item--intercity">
                  <div class="budget-summary-sub-value">¥{{ formatBudgetAmount(interCityTotal) }}</div>
                  <div class="budget-summary-sub-label">
                    {{ budgetIncludeInterCity
                      ? t('result.budget.intercityIncluded')
                      : t('result.budget.intercityExcluded') }}
                  </div>
                </div>
              </div>

              <div v-if="interCityTotal > 0 && interCityPricingMeta" class="budget-intercity-meta">
                {{ interCityPricingMeta }}
              </div>

              <div v-if="interCityTotal > 0 && !budgetIncludeInterCity" class="budget-exclude-note">
                {{ t('result.budget.intercityExcludeNote', { amount: formatBudgetAmount(interCityTotal) }) }}
              </div>

              <div class="budget-pending-wrap">
                <div class="budget-pending-title">{{ t('result.budget.pendingTitle') }}</div>
                <div v-if="pendingBudgetItems.length === 0" class="budget-pending-empty">
                  {{ t('result.budget.pendingEmpty') }}
                </div>
                <div v-else class="budget-pending-list">
                  <div
                    v-for="pendingItem in pendingBudgetItems"
                    :key="pendingItem.uid"
                    class="budget-pending-item"
                  >
                    <span class="budget-pending-name">{{ pendingItem.base.name }}</span>
                    <a-button
                      type="link"
                      size="small"
                      class="budget-restore-btn"
                      @click="restoreBudgetItem(pendingItem)"
                    >
                      {{ t('result.budget.restore') }}
                    </a-button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="right-map" v-show="activeSection === 'map'">
            <a-card id="map" :bordered="false" class="map-card section-shellless">
              <div v-if="mapProviderType === 'amap' && transferSummary" class="map-transfer-pill">{{ transferSummary }}</div>
              <AttractionMapControls
                v-if="mapProviderType === 'amap'"
                :is3d="mapPitch > 10"
                :pick-mode="mapPickMode"
                :label="t('result.map3d.controls')"
                :labels="mapControlLabels"
                @toggle3d="toggleMapDimension"
                @zoom-in="zoomMap(1)"
                @zoom-out="zoomMap(-1)"
                @rotate-left="rotateMap(-45)"
                @rotate-right="rotateMap(45)"
                @north="resetMapNorth"
                @reset="resetMapView"
                @places="openPlacesDrawer"
              />
              <div v-if="mapProviderType === 'amap'" class="map-day-filter">
                <button
                  type="button"
                  class="map-day-chip"
                  :class="{ active: selectedMapDay === 'all' }"
                  @click="selectMapDay('all')"
                >
                  {{ t('result.map3d.allDays') }}
                </button>
                <button
                  v-for="(_, dayIndex) in tripPlan.days"
                  :key="`map-day-${dayIndex}`"
                  type="button"
                  class="map-day-chip"
                  :class="{ active: selectedMapDay === dayIndex }"
                  @click="selectMapDay(dayIndex)"
                >
                  {{ t('common.dayNumber', { day: dayIndex + 1 }) }}
                </button>
              </div>
              <div v-if="mapLoading" class="map-loading-mask" aria-live="polite">
                <span class="map-loading-spinner"></span>
                <span>{{ t('result.mapLoading') }}</span>
              </div>
              <div v-show="mapProviderType === 'amap'" id="amap-container" :class="{ 'map-pick-mode': mapPickMode }" style="width: 100%; height: 100%"></div>
            </a-card>
          </div>
        </div>


        <!-- 每日行程:可折叠 -->
        <a-card v-show="activeSection === 'days'" :bordered="false" class="days-card section-shellless">
          <a-collapse v-model:activeKey="activeDays" accordion>
            <a-collapse-panel
              v-for="(day, index) in tripPlan.days"
              :key="index"
              :id="`day-${index}`"
            >
              <template #header>
                <div class="day-header">
                  <span class="day-title">{{ t('common.dayNumber', { day: index + 1 }) }}</span>
                  <span v-if="day.city" class="day-city-tag">{{ day.city }}</span>
                  <span v-if="day.is_transfer_day" class="day-transfer-tag">{{ t('result.transferDay') }}</span>
                  <span class="day-date">{{ day.date }}</span>
                </div>
              </template>

              <!-- 城际移动信息 -->
              <div v-if="day.is_transfer_day && day.transfer_info" class="transfer-info-banner">
                <span class="transfer-info-icon">🚄</span>
                <span class="transfer-info-label">{{ t('result.transferInfo') }}:</span>
                <span class="transfer-info-text">{{ day.transfer_info }}</span>
              </div>

              <!-- 行程基本信息 -->
              <div class="day-info">
                <div class="info-row">
                  <span class="label">{{ t('result.dayDescription') }}</span>
                  <span class="value">{{ day.description }}</span>
                </div>
                <div class="info-row">
                  <span class="label">{{ t('result.dayTransport') }}</span>
                  <span class="value">{{ day.transportation }}</span>
                </div>
                <div class="info-row">
                  <span class="label">{{ t('result.dayAccommodation') }}</span>
                  <span class="value">{{ day.accommodation }}</span>
                </div>
              </div>

              <ImportantReminders
                v-if="getDayReminders(index).length"
                :items="getDayReminders(index)"
                :heading="t('result.reminders.dayTitle')"
                dense
                class="day-reminders"
              />

              <!-- 景点安排 -->
              <a-divider orientation="left">{{ t('result.attractionTitle') }}</a-divider>
              <a-list
                :data-source="day.attractions"
                :grid="{ gutter: 16, column: 2 }"
              >
                <template #renderItem="{ item, index }">
                  <a-list-item>
                    <a-card :title="item.name" size="small" class="attraction-card">
                      <!-- 编辑模式下的操作按钮 -->
                      <template #extra v-if="editMode">
                        <a-space>
                          <a-button
                            size="small"
                            @click="moveAttraction(day.day_index, index, 'up')"
                            :disabled="index === 0"
                          >
                            Up
                          </a-button>
                          <a-button
                            size="small"
                            @click="moveAttraction(day.day_index, index, 'down')"
                            :disabled="index === day.attractions.length - 1"
                          >
                            Down
                          </a-button>
                          <a-button
                            size="small"
                            danger
                            @click="deleteAttraction(day.day_index, index)"
                          >
                            {{ t('common.delete') }}
                          </a-button>
                        </a-space>
                      </template>

                      <!-- 景点图片 -->
                      <div class="attraction-image-wrapper">
                        <img
                          :src="toDisplayPhotoUrl(item.image_url) || getAttractionImage(item.name, index)"
                          :alt="item.name"
                          class="attraction-image"
                          loading="lazy"
                          decoding="async"
                          referrerpolicy="no-referrer"
                          @error="handleImageError"
                        />
                        <div class="attraction-badge">
                          <span class="badge-number">{{ index + 1 }}</span>
                        </div>
                        <div v-if="item.ticket_price" class="price-tag">
                          <span>¥{{ item.ticket_price }}</span>
                          <span class="price-tag-ref">{{ t('result.referenceOnly') }}</span>
                        </div>
                      </div>

                      <!-- 编辑模式下可编辑的字段 -->
                      <div v-if="editMode">
                        <p><strong>{{ t('result.fieldAddress') }}:</strong></p>
                        <a-input v-model:value="item.address" size="small" style="margin-bottom: 8px" />

                        <p><strong>{{ t('result.fieldVisitDurationMinutes') }}:</strong></p>
                        <a-input-number v-model:value="item.visit_duration" :min="10" :max="480" size="small" style="width: 100%; margin-bottom: 8px" />

                        <p><strong>{{ t('result.fieldDescription') }}:</strong></p>
                        <a-textarea v-model:value="item.description" :rows="2" size="small" style="margin-bottom: 8px" />
                      </div>

                      <!-- 查看模式 -->
                      <div v-else>
                        <p><strong>{{ t('result.fieldAddress') }}:</strong> {{ item.address }}</p>
                        <p><strong>{{ t('result.fieldVisitDuration') }}:</strong> {{ item.visit_duration }}{{ t('result.minuteUnit') }}</p>
                        <p><strong>{{ t('result.fieldDescription') }}:</strong> {{ item.description }}</p>
                        <p v-if="item.rating"><strong>{{ t('result.fieldRating') }}:</strong> {{ item.rating }}</p>
                        <!-- 预约提醒 -->
                        <div v-if="item.reservation_required" class="reservation-alert">
                          <span class="reservation-badge">📋 需提前预约</span>
                          <span v-if="item.reservation_tips" class="reservation-tips">{{ item.reservation_tips }}</span>
                        </div>
                      </div>
                    </a-card>
                  </a-list-item>
                </template>
              </a-list>

              <!-- 酒店推荐 -->
              <a-divider v-if="day.hotel" orientation="left">{{ t('result.hotelTitle') }}</a-divider>
              <a-card v-if="day.hotel" size="small" class="hotel-card">
                <template #title>
                  <span class="hotel-title">{{ day.hotel.name }}</span>
                </template>
                <a-descriptions :column="2" size="small">
                  <a-descriptions-item :label="t('result.fieldAddress')">{{ day.hotel.address }}</a-descriptions-item>
                  <a-descriptions-item :label="t('result.fieldType')">{{ day.hotel.type }}</a-descriptions-item>
                  <a-descriptions-item :label="t('result.fieldPriceRange')">{{ day.hotel.price_range }}</a-descriptions-item>
                  <a-descriptions-item :label="t('result.fieldRating')">{{ day.hotel.rating }}</a-descriptions-item>
                  <a-descriptions-item :label="t('result.fieldDistance')" :span="2">{{ day.hotel.distance }}</a-descriptions-item>
                </a-descriptions>
              </a-card>

              <!-- 餐饮安排 -->
              <a-divider orientation="left">{{ t('result.mealsTitle') }}</a-divider>
              <a-descriptions :column="1" bordered size="small">
                <a-descriptions-item
                  v-for="meal in day.meals"
                  :key="meal.type"
                  :label="getMealLabel(meal.type)"
                >
                  {{ meal.name }}
                  <span v-if="meal.description"> - {{ meal.description }}</span>
                  <span v-if="meal.estimated_cost" class="meal-price-note">
                    {{ t('result.meals.estimatedCost', { amount: formatBudgetAmount(meal.estimated_cost) }) }}
                  </span>
                </a-descriptions-item>
              </a-descriptions>
            </a-collapse-panel>
          </a-collapse>
        </a-card>

        <a-card
          v-show="activeSection === 'weather' && tripPlan.weather_info && tripPlan.weather_info.length > 0"
          id="weather"
          v-if="tripPlan.weather_info && tripPlan.weather_info.length > 0"
          :bordered="false"
          class="section-shellless weather-section-card"
        >
          <div v-if="selectedWeather" class="weather-dashboard">
            <section class="weather-side" :style="weatherSideStyle">
              <div class="weather-gradient"></div>

              <div class="date-container">
                <h2 class="date-dayname">{{ formatWeatherWeekday(selectedWeather.date) }}</h2>
                <span class="date-day">{{ formatWeatherDate(selectedWeather.date) }}</span>
                <span class="location">
                  <span class="location-icon">
                    <svg width="16px" height="16px" viewBox="-3 0 20 20" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
                        <g id="Page-1" stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
                            <g id="Dribbble-Light-Preview" transform="translate(-223.000000, -5439.000000)" fill="currentColor">
                                <g id="icons" transform="translate(56.000000, 160.000000)">
                                    <path d="M176,5286.219 C176,5287.324 175.105,5288.219 174,5288.219 C172.895,5288.219 172,5287.324 172,5286.219 C172,5285.114 172.895,5284.219 174,5284.219 C175.105,5284.219 176,5285.114 176,5286.219 M174,5296 C174,5296 169,5289 169,5286 C169,5283.243 171.243,5281 174,5281 C176.757,5281 179,5283.243 179,5286 C179,5289 174,5296 174,5296 M174,5279 C170.134,5279 167,5282.134 167,5286 C167,5289.866 174,5299 174,5299 C174,5299 181,5289.866 181,5286 C181,5282.134 177.866,5279 174,5279" id="pin_sharp_circle-[#624]"></path>
                                </g>
                            </g>
                        </g>
                    </svg>
                  </span>
                  {{ selectedWeather?.city || tripPlan.city }}
                </span>
              </div>

              <div class="weather-container">
                <div class="weather-hero-icon weather-icon" :class="selectedWeatherIconKind">
                  <template v-if="selectedWeatherIconKind === 'sun-shower'">
                    <div class="cloud"></div>
                    <div class="sun">
                      <div class="rays"></div>
                    </div>
                    <div class="rain"></div>
                  </template>
                  <template v-else-if="selectedWeatherIconKind === 'thunder-storm'">
                    <div class="cloud"></div>
                    <div class="lightning">
                      <div class="bolt"></div>
                      <div class="bolt"></div>
                    </div>
                  </template>
                  <template v-else-if="selectedWeatherIconKind === 'cloudy'">
                    <div class="cloud"></div>
                    <div class="cloud"></div>
                  </template>
                  <template v-else-if="selectedWeatherIconKind === 'flurries'">
                    <div class="cloud"></div>
                    <div class="snow">
                      <div class="flake"></div>
                      <div class="flake"></div>
                    </div>
                  </template>
                  <template v-else-if="selectedWeatherIconKind === 'rainy'">
                    <div class="cloud"></div>
                    <div class="rain"></div>
                  </template>
                  <template v-else>
                    <div class="sun">
                      <div class="rays"></div>
                    </div>
                  </template>
                </div>
                <h1 class="weather-temp">{{ formatWeatherTemp(selectedWeather.day_temp) }}</h1>
                <h3 class="weather-desc">{{ selectedWeather.day_weather }}</h3>
              </div>
            </section>

            <section class="weather-info-side">
              <div class="week-container week-container--top">
                <ul class="week-list">
                  <li
                    v-for="(weatherItem, weatherIndex) in weatherDisplayList"
                    :key="`${weatherItem.date}-${weatherIndex}`"
                    :class="{ active: weatherIndex === activeWeatherIndex }"
                    @mouseenter="selectWeatherDay(weatherIndex)"
                    @click="selectWeatherDay(weatherIndex)"
                  >
                    <div class="day-icon weather-icon weather-icon--small" :class="weatherItem._iconKind">
                      <template v-if="weatherItem._iconKind === 'sun-shower'">
                        <div class="cloud"></div>
                        <div class="sun">
                          <div class="rays"></div>
                        </div>
                        <div class="rain"></div>
                      </template>
                      <template v-else-if="weatherItem._iconKind === 'thunder-storm'">
                        <div class="cloud"></div>
                        <div class="lightning">
                          <div class="bolt"></div>
                          <div class="bolt"></div>
                        </div>
                      </template>
                      <template v-else-if="weatherItem._iconKind === 'cloudy'">
                        <div class="cloud"></div>
                        <div class="cloud"></div>
                      </template>
                      <template v-else-if="weatherItem._iconKind === 'flurries'">
                        <div class="cloud"></div>
                        <div class="snow">
                          <div class="flake"></div>
                          <div class="flake"></div>
                        </div>
                      </template>
                      <template v-else-if="weatherItem._iconKind === 'rainy'">
                        <div class="cloud"></div>
                        <div class="rain"></div>
                      </template>
                      <template v-else>
                        <div class="sun">
                          <div class="rays"></div>
                        </div>
                      </template>
                    </div>
                    <span class="day-name">{{ formatWeatherWeekday(weatherItem.date, true) }}</span>
                    <span class="day-temp">{{ formatWeatherTemp(weatherItem.day_temp) }}</span>
                  </li>
                </ul>
              </div>

              <div class="today-info-container">
                <div class="today-info">
                  <div class="today-info-item">
                    <span class="wea-title">{{ t('result.weatherDay') }}</span>
                    <span class="value">{{ selectedWeather.day_weather }} · {{ formatWeatherTemp(selectedWeather.day_temp) }}</span>
                  </div>
                  <div class="today-info-item">
                    <span class="wea-title">{{ t('result.weatherNight') }}</span>
                    <span class="value">{{ selectedWeather.night_weather }} · {{ formatWeatherTemp(selectedWeather.night_temp) }}</span>
                  </div>
                  <div class="today-info-item">
                    <span class="wea-title">{{ t('result.weatherPrecipitation') }}</span>
                    <span class="value">{{ getWeatherPrecipitation(selectedWeather.day_weather) }}</span>
                  </div>
                  <div class="today-info-item">
                    <span class="wea-title">{{ t('result.weatherHumidity') }}</span>
                    <span class="value">{{ getWeatherHumidity(selectedWeather.day_weather) }}</span>
                  </div>
                  <div class="today-info-item">
                    <span class="wea-title">{{ t('result.weatherWind') }}</span>
                    <span class="value">{{ getWeatherWind(selectedWeather) }}</span>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </a-card>
      </div>

      <div v-else class="empty-state-panel">
        <a-empty :description="t('result.noTripPlan')">
          <template #description>
            <span class="empty-desc">{{ t('result.noTripPlanDesc') }}</span>
          </template>
          <a-button class="empty-back-btn" type="primary" @click="goBack">{{ t('result.backCreateTrip') }}</a-button>
        </a-empty>
      </div>
    </main>

    <!-- “更换阶段”：全屏锁定，背景内容通过 inert 一并禁止交互 -->
    <div v-if="discoverUpdating" class="phase-lock-overlay" role="alert" aria-live="assertive">
      <div class="phase-lock-card">
        <span class="phase-lock-spinner"></span>
        <p>{{ t('result.discover.updating') }}</p>
      </div>
    </div>

    <!-- 回到顶部按钮 -->
    <a-back-top :visibility-height="300">
      <div class="back-top-button">
        Top
      </div>
    </a-back-top>
    <!-- 地点管理抽屉 -->
    <a-drawer
      v-model:open="placesDrawerOpen"
      :mask="false"
      placement="right"
      width="min(420px, 100vw)"
      :body-style="{ padding: '14px 16px 20px' }"
      class="places-drawer"
    >
      <template #title>
        <div class="places-drawer__title">
          <span>地点管理</span>
          <span class="places-drawer__count">{{ places.length }}</span>
        </div>
      </template>

      <div v-if="placeFormOpen" class="place-editor">
        <div class="place-editor__head">
          <strong>{{ editingPlace ? '编辑地点' : '添加地点' }}</strong>
          <a-button type="text" size="small" @click="closePlaceForm">取消</a-button>
        </div>

        <div class="place-search-row">
          <a-input
            v-model:value="placeSearchKeyword"
            placeholder="搜索高德地点，如：大雁塔"
            allow-clear
            @press-enter="searchAmapPlaces"
          />
          <a-button :loading="placeSearching" @click="searchAmapPlaces">搜索</a-button>
        </div>
        <div v-if="placeSearchResults.length" class="place-search-results">
          <button
            v-for="poi in placeSearchResults"
            :key="poi.id"
            type="button"
            class="place-poi"
            @click="pickPoi(poi)"
          >
            <strong>{{ poi.name }}</strong>
            <span>{{ poi.address }}</span>
          </button>
        </div>

        <div class="place-form">
          <label>名称</label>
          <a-input v-model:value="placeForm.name" placeholder="地点名称" :maxlength="80" />
          <label>类型</label>
          <a-select v-model:value="placeForm.type" :options="placeTypeOptions" :disabled="!!editingPlace" />
          <label>所属天</label>
          <a-select v-model:value="placeForm.day_index" :options="placeDayOptions" :disabled="!!editingPlace" />
          <label>地址</label>
          <a-input v-model:value="placeForm.address" placeholder="地址（可自动回填）" :maxlength="200" />
          <label>坐标（GCJ-02）</label>
          <div class="place-coord-row">
            <a-input-number
              v-model:value="placeForm.longitude"
              :step="0.0001"
              :precision="6"
              placeholder="经度"
              style="width: 100%"
            />
            <a-input-number
              v-model:value="placeForm.latitude"
              :step="0.0001"
              :precision="6"
              placeholder="纬度"
              style="width: 100%"
            />
          </div>
          <a-button
            size="small"
            :type="mapPickMode ? 'primary' : 'default'"
            class="place-pick-btn"
            @click="toggleMapPick"
          >
            {{ mapPickMode ? '请点击地图选点…' : '在地图上选点' }}
          </a-button>
          <label>建议停留（分钟）</label>
          <a-input-number v-model:value="placeForm.visit_duration_min" :min="0" :max="1440" style="width: 100%" />
          <label>备注</label>
          <a-textarea v-model:value="placeForm.note" :rows="2" placeholder="备注（可选）" :maxlength="500" />
          <div v-if="placeSaving" class="place-save-status">
            {{ placeSavingPhase || '正在处理，请稍候…' }}
          </div>
          <a-button type="primary" block :loading="placeSaving" @click="savePlace">
            {{ placeSaving ? '处理中…' : (editingPlace ? '保存修改' : '添加地点') }}
          </a-button>
        </div>
      </div>

      <template v-else>
        <div class="place-topbar">
          <span class="place-topbar__hint">酒店与想去的地点都会显示在地图上</span>
          <a-button size="small" type="primary" @click="openPlaceForm()">添加地点</a-button>
        </div>
        <div class="place-filter">
          <button
            v-for="filter in placeFilters"
            :key="filter.value"
            type="button"
            class="map-day-chip"
            :class="{ active: placeFilter === filter.value }"
            @click="placeFilter = filter.value"
          >
            {{ filter.label }}
          </button>
        </div>

        <a-spin :spinning="placesLoading">
          <div v-if="!filteredPlaces.length" class="place-empty">
            <div class="place-empty__title">还没有地点</div>
            <div class="place-empty__desc">搜索高德地点，或在地图上选点添加酒店和想去的地方。</div>
          </div>
          <div v-else class="place-list">
            <div
              v-for="place in filteredPlaces"
              :key="place.id"
              class="place-item"
              :class="{ selected: selectedPlaceId === place.id }"
              @click="focusPlace(place)"
            >
              <div class="place-item__main">
                <span class="place-type">{{ placeTypeLabel(place.type) }}</span>
                <strong class="place-name">{{ place.name }}</strong>
                <span class="place-day">{{ place.day_index === null ? '未分配' : `第 ${place.day_index + 1} 天` }}</span>
              </div>
              <div class="place-item__addr">{{ place.address || '—' }}</div>
              <div class="place-item__price">
                <template v-if="place.price != null && place.price > 0">
                  参考价格 ¥{{ formatBudgetAmount(place.price) }}（{{ t('result.referenceOnly') }}）
                  <span v-if="place.price_source === 'amap'">（实时查询）</span>
                </template>
                <template v-else>未查询到可用价格，未计入预算</template>
              </div>
              <div class="place-item__actions" @click.stop>
                <a-button type="link" size="small" @click="openPlaceForm(place)">编辑</a-button>
                <a-popconfirm title="删除该地点？删除后路线会自动重算。" @confirm="removePlace(place)">
                  <a-button type="link" size="small" danger>删除</a-button>
                </a-popconfirm>
              </div>
            </div>
          </div>
        </a-spin>
      </template>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { message } from 'ant-design-vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import html2canvas from 'html2canvas'
import NavBar from '@/components/NavBar.vue'
import OverviewAttractionCard from '@/components/OverviewAttractionCard.vue'
import OverviewAttractionDetail from '@/components/OverviewAttractionDetail.vue'
import AttractionMapControls from '@/components/AttractionMapControls.vue'
import ImportantReminders from '@/components/ImportantReminders.vue'
import { fetchAttractionGuide, type AttractionGuide } from '@/services/attractionGuide'
import { fetchPopularAttractions, type PopularAttraction } from '@/services/popularAttractions'
import { extractPlanReminders, type PlanReminder } from '@/services/reminders'
import type { TripPlan, TripPlanResponse, Attraction, Meal, Hotel, WeatherInfo } from '@/types'
import {
  listPlaces,
  createPlace,
  updatePlace,
  deletePlace,
  type Place,
  type PlaceType,
} from '@/services/places'
import {
  getRuntimeApiBaseUrl,
  getRuntimeMapJsKey,
  setRuntimeMapJsKey,
  getBackendRuntimeSettings,
  ensureAmapSecurityConfig,
  pollTaskStatus,
  RUNTIME_SETTINGS_UPDATED_EVENT,
} from '@/services/api'

const router = useRouter()
const route = useRoute()
const { t, locale } = useI18n()
const tripPlan = ref<TripPlan | null>(null)
const planId = ref('')
const editMode = ref(false)
const originalPlan = ref<TripPlan | null>(null)
const tripFormMeta = ref<{ origin?: string; intercity_transportation?: string; intercity_seat_type?: string; transportation?: string }>({})
const attractionPhotos = ref<Record<string, string>>({})
const attractionPhotoGalleries = ref<Record<string, string[]>>({})
const activeSection = ref('overview')
const activeDays = ref<number[]>([0]) // 默认展开第一天
const overviewDetailItem = ref<OverviewAttractionItem | null>(null)
const overviewGuide = ref<AttractionGuide | null>(null)
const overviewGuideLoading = ref(false)
const overviewGuideError = ref('')
const overviewGuideCache = new Map<string, AttractionGuide>()
let overviewGuideRequestId = 0
// ===== 热门景点发现页 =====
const popularAttractions = ref<PopularAttraction[]>([])
const popularLoading = ref(false)
const popularError = ref('')
const popularLoadedCity = ref('')
const discoverDetail = ref<PopularAttraction | null>(null)
const discoverGuide = ref<AttractionGuide | null>(null)
const discoverGuideLoading = ref(false)
const discoverGuideError = ref('')
const discoverGuideCache = new Map<string, AttractionGuide>()
let discoverGuideRequestId = 0
const discoverAddDay = ref(0)
const discoverAddingId = ref('')
const discoverUpdating = ref(false)
const mapRefreshing = ref(false)
const mapLoading = ref(false)
let mapRefreshQueued = false
let queuedMapRefreshOptions: MapRenderOptions | null = null
let map: any = null
const mapProviderType = ref<'amap'>('amap')
const mapPitch = ref(45)
const mapRotation = ref(0)
const selectedMapDay = ref<number | 'all'>('all')
// 程序化相机动画期间屏蔽 AMap 的逐帧事件，避免整页 Vue 重渲染与 WebGL 抢帧
let cameraAnimating = false
let cameraSyncTimer: number | null = null
let mapUnhealthy = false
let amapMarkers: any[] = []
// 每个 marker 都带一个 InfoWindow；不关闭会在反复渲染/切换日期时堆积 DOM 与事件，
// 表现为 3D 地图越用越卡（刷新页面才恢复）。
let amapInfoWindows: any[] = []
// SDK 需要的插件清单：预加载与正式初始化共用，避免两处不一致。
const AMAP_PLUGIN_LIST = [
  'AMap.Marker',
  'AMap.Polyline',
  'AMap.InfoWindow',
  'AMap.Driving',
  'AMap.Walking',
  'AMap.ControlBar',
  'AMap.Scale',
  'AMap.PlaceSearch',
  'AMap.Transfer',
  'AMap.Geocoder',
]
let amapLoaderPromise: Promise<any> | null = null
let amapInstance: any = null
let amapRouteOverlays: any[] = []
let amapRouteLabels: any[] = []
let amapRenderToken = 0
let mapDirty = false
const routeCache = new Map<string, { path: RoutePoint[]; durationSec: number; distanceM: number } | null>()
const geoCache = new Map<string, RoutePoint | null>()
let mapInitGeneration = 0

const mapControlLabels = computed(() => ({
  toggle3d: t('result.map3d.toggle3d'),
  zoom: t('result.map3d.zoom'),
  zoomIn: t('result.map3d.zoomIn'),
  zoomOut: t('result.map3d.zoomOut'),
  rotate: t('result.map3d.rotate'),
  rotateLeft: t('result.map3d.rotateLeft'),
  rotateRight: t('result.map3d.rotateRight'),
  north: t('result.map3d.north'),
  reset: t('result.map3d.reset'),
  places: t('result.map3d.places'),
}))

// ===== 地点管理 =====
type PlaceFilter = 'all' | PlaceType
const placesDrawerOpen = ref(false)
const places = ref<Place[]>([])
const placesLoading = ref(false)
const placeFilter = ref<PlaceFilter>('all')
const placeFormOpen = ref(false)
const editingPlace = ref<Place | null>(null)
const placeSaving = ref(false)
const placeSavingPhase = ref('')
const placeSearchKeyword = ref('')
const placeSearchResults = ref<any[]>([])
const placeSearching = ref(false)
const mapPickMode = ref(false)
const transferSummary = ref('')
const selectedPlaceId = ref('')
let amapGeocoder: any = null
const placeForm = reactive<{
  name: string
  type: PlaceType
  day_index: number | null
  address: string
  longitude: number | null
  latitude: number | null
  note: string
  visit_duration_min: number | null
  amap_poi_id: string | null
}>({
  name: '',
  type: 'attraction',
  day_index: 0,
  address: '',
  longitude: null,
  latitude: null,
  note: '',
  visit_duration_min: 60,
  amap_poi_id: null,
})

const placeFilters = computed(() => [
  { value: 'all' as PlaceFilter, label: '全部' },
  { value: 'hotel' as PlaceFilter, label: '酒店' },
  { value: 'attraction' as PlaceFilter, label: '景点' },
  { value: 'restaurant' as PlaceFilter, label: '餐饮' },
  { value: 'station' as PlaceFilter, label: '车站' },
  { value: 'custom' as PlaceFilter, label: '其他' },
])

const filteredPlaces = computed(() => {
  if (placeFilter.value === 'all') return places.value
  return places.value.filter((place) => place.type === placeFilter.value)
})

const placeTypeOptions = [
  { value: 'hotel', label: '酒店' },
  { value: 'attraction', label: '景点' },
  { value: 'restaurant', label: '餐饮' },
  { value: 'station', label: '车站' },
  { value: 'custom', label: '自定义' },
]

const placeDayOptions = computed(() => {
  const options = [{ value: null as number | null, label: '未分配' }]
  ;(tripPlan.value?.days || []).forEach((day, index) => {
    options.push({ value: index, label: `第 ${index + 1} 天 · ${day.date}` })
  })
  return options
})

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

type BudgetItemType = 'attraction' | 'hotel' | 'meal' | 'transport'
type BudgetSortMode = 'playOrder' | 'amountDesc' | 'amountAsc' | 'dayAsc' | 'dayDesc' | 'custom'

type BudgetDetailItem = {
  id: string
  type: BudgetItemType
  dayIndex: number | null
  dayNumber: number | null
  name: string
  amount: number
  sourceIndex?: number
}

type BudgetRestorePayload =
  | {
      type: 'attraction'
      attraction: Attraction
      insertIndex: number
    }
  | {
      type: 'meal'
      meal: Meal
      insertIndex: number
    }
  | {
      type: 'hotel'
      hotel: Hotel
      accommodation: string
    }
  | {
      type: 'transport'
      transportation: string
    }

type BudgetRestoreItem = {
  uid: string
  base: BudgetDetailItem
  payload: BudgetRestorePayload
}

const budgetFilterType = ref<'all' | BudgetItemType>('all')
const budgetFilterDay = ref<number | 'all'>('all')
const budgetSortMode = ref<BudgetSortMode>('playOrder')
const budgetCustomOrder = ref<string[]>([])
const editingBudgetId = ref('')
const budgetEditDraft = ref<number | null>(0)
const pendingBudgetItems = ref<BudgetRestoreItem[]>([])
const activeWeatherIndex = ref(0)

const localeTag = computed(() => {
  const currentLocale = String(locale.value || 'en').toLowerCase()
  if (currentLocale.startsWith('zh')) return 'zh-CN'
  if (currentLocale.startsWith('ja')) return 'ja-JP'
  return 'en-US'
})

const weatherList = computed<WeatherInfo[]>(() => tripPlan.value?.weather_info ?? [])

const selectedWeather = computed<WeatherInfo | null>(() => {
  const list = weatherList.value
  if (list.length === 0) return null
  const safeIndex = Math.min(Math.max(activeWeatherIndex.value, 0), list.length - 1)
  return list[safeIndex]
})

const parseWeatherDate = (rawDate: string): Date | null => {
  if (!rawDate) return null

  const normalized = rawDate
    .replace(/年/g, '-')
    .replace(/月/g, '-')
    .replace(/日/g, '')
    .replace(/[./]/g, '-')
    .trim()

  const parsedDate = new Date(normalized)
  if (!Number.isNaN(parsedDate.getTime())) return parsedDate

  const matched = rawDate.match(/(\d{4})\D+(\d{1,2})\D+(\d{1,2})/)
  if (!matched) return null
  const [, year, month, day] = matched
  const fallbackDate = new Date(Number(year), Number(month) - 1, Number(day))
  return Number.isNaN(fallbackDate.getTime()) ? null : fallbackDate
}

const formatWeatherDate = (rawDate: string): string => {
  const date = parseWeatherDate(rawDate)
  if (!date) return rawDate || '--'
  return new Intl.DateTimeFormat(localeTag.value, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(date)
}

const formatWeatherWeekday = (rawDate: string, short = false): string => {
  const date = parseWeatherDate(rawDate)
  if (!date) return rawDate || '--'
  return new Intl.DateTimeFormat(localeTag.value, {
    weekday: short ? 'short' : 'long',
  }).format(date)
}

const formatWeatherTemp = (temperature: number | null | undefined): string => {
  if (!Number.isFinite(Number(temperature))) return '--'
  return `${Math.round(Number(temperature))}°C`
}

type WeatherIconKind = 'sun-shower' | 'thunder-storm' | 'cloudy' | 'flurries' | 'sunny' | 'rainy'

const getWeatherIconKind = (weatherText: string): WeatherIconKind => {
  const text = (weatherText || '').trim()
  const hasRain = /(雨|rain|shower|drizzle|sprinkle|阵雨|小雨|中雨|大雨|暴雨)/i.test(text)
  const hasSun = /(晴|sun|clear)/i.test(text)

  if (/(雷|thunder|storm|lightning|雷暴|雷阵雨)/i.test(text)) return 'thunder-storm'
  if (/(雪|snow|sleet|hail|冰雹|冻雨|雨夹雪)/i.test(text)) return 'flurries'
  if (hasRain && hasSun) return 'sun-shower'
  if (hasRain) return 'rainy'
  if (/(云|阴|cloud|overcast|雾|霾|fog|mist|haze|wind|breeze|gale)/i.test(text)) return 'cloudy'
  return 'sunny'
}

const selectedWeatherIconKind = computed<WeatherIconKind>(() => {
  if (!selectedWeather.value) return 'sunny'
  return getWeatherIconKind(`${selectedWeather.value.day_weather || ''} ${selectedWeather.value.night_weather || ''}`)
})

type WeatherDisplayItem = WeatherInfo & {
  _iconKind: WeatherIconKind
}

const weatherDisplayList = computed<WeatherDisplayItem[]>(() => {
  return weatherList.value.map((item) => ({
    ...item,
    _iconKind: getWeatherIconKind(`${item.day_weather || ''} ${item.night_weather || ''}`),
  }))
})

const getWeatherGradient = (weatherText: string): string => {
  const text = (weatherText || '').toLowerCase()
  if (/(雷|thunder)/.test(text)) return 'linear-gradient(140deg, #3a4a86 0%, #5b3b8a 100%)'
  if (/(雪|snow|sleet|hail)/.test(text)) return 'linear-gradient(140deg, #8bc6ec 0%, #d9afd9 100%)'
  if (/(雨|rain|shower|drizzle)/.test(text)) return 'linear-gradient(140deg, #4b6cb7 0%, #182848 100%)'
  if (/(雾|霾|fog|mist|haze)/.test(text)) return 'linear-gradient(140deg, #7b8799 0%, #4a5568 100%)'
  if (/(阴|cloud|overcast)/.test(text)) return 'linear-gradient(140deg, #6d7f92 0%, #3f4c6b 100%)'
  return 'linear-gradient(140deg, #72edf2 0%, #5151e5 100%)'
}

const getWeatherPrecipitation = (weatherText: string): string => {
  const text = (weatherText || '').toLowerCase()
  if (/(雷|thunder|暴雨|storm)/.test(text)) return '85%'
  if (/(雨|rain|shower|drizzle)/.test(text)) return '65%'
  if (/(雪|snow|sleet|hail)/.test(text)) return '55%'
  if (/(阴|cloud|overcast)/.test(text)) return '30%'
  return '10%'
}

const getWeatherHumidity = (weatherText: string): string => {
  const text = (weatherText || '').toLowerCase()
  if (/(雷|thunder|暴雨|storm)/.test(text)) return '88%'
  if (/(雨|rain|shower|drizzle)/.test(text)) return '78%'
  if (/(雪|snow|sleet|hail)/.test(text)) return '72%'
  if (/(阴|cloud|overcast|雾|霾|fog|mist|haze)/.test(text)) return '62%'
  return '42%'
}

const getWeatherWind = (weather: WeatherInfo | null): string => {
  if (!weather) return '--'
  const direction = weather.wind_direction?.trim() || '--'
  const power = weather.wind_power?.trim() || '--'
  return `${direction} ${power}`.trim()
}

const selectWeatherDay = (index: number) => {
  if (index < 0 || index >= weatherList.value.length) return
  activeWeatherIndex.value = index
}

const weatherSideStyle = computed<Record<string, string>>(() => ({
  '--weather-gradient': getWeatherGradient(selectedWeather.value?.day_weather || ''),
}))

watch(
  weatherList,
  (list) => {
    if (list.length === 0) {
      activeWeatherIndex.value = 0
      return
    }

    if (activeWeatherIndex.value > list.length - 1) {
      activeWeatherIndex.value = 0
    }
  },
  { immediate: true }
)

const overviewAttractions = computed<OverviewAttractionItem[]>(() => {
  if (!tripPlan.value) return []

  const items: OverviewAttractionItem[] = []
  tripPlan.value.days.forEach((day, dayArrayIndex) => {
    const dayNumber = dayArrayIndex + 1

    day.attractions.forEach((attraction, order) => {
      items.push({
        name: attraction.name,
        address: attraction.address,
        visit_duration: attraction.visit_duration,
        description: attraction.description,
        category: attraction.category,
        ticket_price: attraction.ticket_price,
        dayNumber,
        dayArrayIndex,
        order,
      })
    })
  })
  return items
})

const currentAttractionNames = computed<string[]>(() =>
  (tripPlan.value?.days || [])
    .flatMap((day) => day.attractions || [])
    .map((attraction) => attraction.name)
    .filter(Boolean)
)

const discoverDayOptions = computed(() =>
  (tripPlan.value?.days || []).map((day, index) => ({
    value: index,
    label: `${t('common.dayNumber', { day: index + 1 })} · ${day.date}`,
  }))
)

const overviewDetailImages = computed<string[]>(() => {
  const item = overviewDetailItem.value
  if (!item) return []

  const urls: string[] = []
  const add = (value?: string | null) => {
    const src = String(value || '').trim()
    if (src && !urls.includes(src)) urls.push(src)
  }

  // 高德实拍图库（通常 3 张）；没有图库时才退回卡片首图
  const gallery = attractionPhotoGalleries.value[item.name] || []
  for (const photo of gallery) {
    add(photo)
  }
  if (gallery.length === 0) {
    add(getAttractionImage(item.name, item.order))
  }

  // 若行程数据本身带了图片，也一并纳入
  const planAttraction = tripPlan.value?.days?.[item.dayArrayIndex]?.attractions?.[item.order]
  add(toDisplayPhotoUrl(planAttraction?.image_url))
  for (const photo of planAttraction?.photos || []) {
    add(toDisplayPhotoUrl(photo))
  }

  return urls.slice(0, 3)
})

const planReminders = computed<PlanReminder[]>(() =>
  tripPlan.value ? extractPlanReminders(tripPlan.value) : []
)

const overviewReminders = computed<PlanReminder[]>(() =>
  [...planReminders.value]
    .sort((a, b) => Number(b.tone === 'important') - Number(a.tone === 'important'))
    .slice(0, 6)
)

const remindersByDay = computed<Map<number, PlanReminder[]>>(() => {
  const map = new Map<number, PlanReminder[]>()
  for (const reminder of planReminders.value) {
    if (reminder.dayIndex < 0) continue
    const list = map.get(reminder.dayIndex) || []
    list.push(reminder)
    map.set(reminder.dayIndex, list)
  }
  return map
})

const getDayReminders = (dayIndex: number): PlanReminder[] =>
  remindersByDay.value.get(dayIndex) || []

const applyTripPlanPayload = async (payload: {
  plan: TripPlan

  planId?: string
}) => {
  tripPlan.value = payload.plan
  resetDayRouteLegs()
  ensureBudgetMetadata()
  recalculateBudgetTotals()
  pendingBudgetItems.value = []
  budgetFilterDay.value = 'all'
  budgetCustomOrder.value = []
  cancelBudgetEdit()

  if (payload.planId) {
    planId.value = payload.planId
    sessionStorage.setItem('planId', payload.planId)
  }

  sessionStorage.setItem('tripPlan', JSON.stringify(payload.plan))


  await loadAttractionPhotos()
  prefetchOverviewGuides()
  // 空闲时预加载高德 SDK，减少首次切到地图时的脚本下载与解析等待
  if (typeof window !== 'undefined') {
    const idle = (window as any).requestIdleCallback as
      | ((cb: () => void, opts?: { timeout: number }) => void)
      | undefined
    if (idle) idle(() => primeAmapSdk(), { timeout: 2500 })
    else window.setTimeout(primeAmapSdk, 1200)
  }
  if (activeSection.value === 'map') await ensureMapReady()
}

const restoreTripPlanFromResponse = async (response?: TripPlanResponse | null) => {
  if (!response?.data) return false
  await applyTripPlanPayload({
    plan: response.data,
    planId: String(response.plan_id || planId.value || ''),
  })
  return true
}

// ===== 地点管理逻辑 =====
const placeTypeLabel = (type: PlaceType): string => {
  const found = placeTypeOptions.find((item) => item.value === type)
  return found?.label || type
}

const loadPlaces = async () => {
  if (!planId.value) return
  placesLoading.value = true
  try {
    places.value = await listPlaces(planId.value)
  } catch (error: any) {
    console.error('加载地点失败:', error)
    message.error(error?.message || '加载地点失败')
  } finally {
    placesLoading.value = false
  }
}

const openPlacesDrawer = () => {
  placesDrawerOpen.value = true
  void loadPlaces()
}

const openPlaceForm = (place?: Place) => {
  editingPlace.value = place || null
  placeFormOpen.value = true
  mapPickMode.value = false
  placeSearchKeyword.value = ''
  placeSearchResults.value = []

  if (place) {
    placeForm.name = place.name
    placeForm.type = place.type
    placeForm.day_index = place.day_index
    placeForm.address = place.address
    placeForm.longitude = place.location.longitude
    placeForm.latitude = place.location.latitude
    placeForm.note = place.note
    placeForm.visit_duration_min = place.visit_duration_min
    placeForm.amap_poi_id = place.amap_poi_id
    return
  }

  const defaultDay = selectedMapDay.value === 'all' ? 0 : selectedMapDay.value
  placeForm.name = ''
  placeForm.type = 'attraction'
  placeForm.day_index = defaultDay
  placeForm.address = ''
  placeForm.longitude = null
  placeForm.latitude = null
  placeForm.note = ''
  placeForm.visit_duration_min = 60
  placeForm.amap_poi_id = null
}

const closePlaceForm = () => {
  placeFormOpen.value = false
  editingPlace.value = null
  mapPickMode.value = false
  placeSearchResults.value = []
}

const searchAmapPlaces = () => {
  const keyword = placeSearchKeyword.value.trim()
  if (!keyword) {
    message.info('请输入要搜索的地点名称')
    return
  }
  if (!amapInstance?.PlaceSearch) {
    message.warning('地图尚未加载，请稍后重试')
    return
  }
  placeSearching.value = true
  const search = new amapInstance.PlaceSearch({
    city: tripPlan.value?.city || '全国',
    pageSize: 8,
    pageIndex: 1,
  })
  search.search(keyword, (status: string, result: any) => {
    placeSearching.value = false
    if (status !== 'complete') {
      placeSearchResults.value = []
      message.warning('没有找到匹配地点')
      return
    }
    placeSearchResults.value = result?.poiList?.pois || []
  })
}

const pickPoi = (poi: any) => {
  placeForm.name = String(poi?.name || '')
  placeForm.address = String(poi?.address || poi?.pname || '')
  const lng = Number(poi?.location?.lng)
  const lat = Number(poi?.location?.lat)
  if (Number.isFinite(lng) && Number.isFinite(lat)) {
    placeForm.longitude = lng
    placeForm.latitude = lat
  }
  placeForm.amap_poi_id = poi?.id || null
  placeSearchResults.value = []
}

const toggleMapPick = () => {
  if (!map) {
    message.warning('地图尚未加载，请稍后重试')
    return
  }
  mapPickMode.value = !mapPickMode.value
  if (mapPickMode.value) {
    message.info('请在地图上点击选择位置')
  }
}

const handleMapClick = (event: any) => {
  if (!mapPickMode.value) return
  const lng = Number(event?.lnglat?.getLng?.())
  const lat = Number(event?.lnglat?.getLat?.())
  if (!Number.isFinite(lng) || !Number.isFinite(lat)) return
  placeForm.longitude = lng
  placeForm.latitude = lat
  mapPickMode.value = false

  if (!amapGeocoder) return
  amapGeocoder.getAddress([lng, lat], (status: string, result: any) => {
    if (status === 'complete' && result?.regeocode?.formattedAddress) {
      placeForm.address = result.regeocode.formattedAddress
    }
  })
}

const refreshAfterPlaceChange = async (options: { openDrawer?: boolean } = {}) => {
  if (!planId.value) return
  const mapWasActive = activeSection.value === 'map'
  try {
    placeSavingPhase.value = '正在刷新行程与预算…'
    const task = await pollTaskStatus(planId.value)
    if (task?.status === 'completed' && task.result) {
      // 不再销毁并重建地图：地点增删改只需要重绘覆盖物。
      // 旧实现 destroy + init 两次 ensureMapReady 会产生渲染 token 竞态，
      // 后一次初始化会取消前一次尚未完成的路线绘制，表现为导航线丢失。
      await restoreTripPlanFromResponse(task.result)
      mapDirty = true
      popularLoadedCity.value = ''
      await nextTick()
      if (mapWasActive) {
        placeSavingPhase.value = '正在重新计算地图路线…'
        mapDirty = false
        await refreshMap({ preserveCamera: true })
      }
    }
  } catch (error) {
    console.warn('刷新行程失败:', error)
  }
  placeSavingPhase.value = '正在加载地点列表…'
  await loadPlaces()
  if (options.openDrawer !== false) {
    placesDrawerOpen.value = true
  }
}

const savePlace = async () => {
  if (!planId.value) return
  const name = placeForm.name.trim()
  const lng = Number(placeForm.longitude)
  const lat = Number(placeForm.latitude)
  if (!name) {
    message.warning('请填写地点名称')
    return
  }
  if (!Number.isFinite(lng) || !Number.isFinite(lat)) {
    message.warning('请选择坐标或在地图上选点')
    return
  }

  placeSaving.value = true
  placeSavingPhase.value = '正在实时查询价格并分析地点类型…'
  try {
    const payload = {
      day_index: placeForm.day_index,
      type: placeForm.type,
      name,
      address: placeForm.address.trim(),
      location: { longitude: lng, latitude: lat },
      note: placeForm.note.trim(),
      visit_duration_min: placeForm.visit_duration_min,
      amap_poi_id: placeForm.amap_poi_id,
      source: placeForm.amap_poi_id ? ('amap' as const) : ('user' as const),
    }
    let saved: Place
    if (editingPlace.value) {
      saved = await updatePlace(planId.value, editingPlace.value.id, {
        ...payload,
        version: editingPlace.value.version,
      })
      message.success(saved.itinerary_adjusted
        ? (saved.adjustment_message || '地点已更新，行程与预算已同步调整')
        : '地点已更新')
    } else {
      saved = await createPlace(planId.value, payload)
      if (saved.price_available && saved.price != null) {
        message.success(`地点已添加，参考价格 ¥${formatBudgetAmount(saved.price)}（仅供参考），已计入预算`)
      } else {
        message.warning(saved.adjustment_message || '地点已添加；未查询到可用价格，未计入预算')
      }
    }
    closePlaceForm()
    await refreshAfterPlaceChange()
  } catch (error: any) {
    message.error(error?.message || '保存地点失败')
  } finally {
    placeSaving.value = false
    placeSavingPhase.value = ''
  }
}

const removePlace = async (place: Place) => {
  if (!planId.value) return
  try {
    await deletePlace(planId.value, place.id)
    if (selectedPlaceId.value === place.id) selectedPlaceId.value = ''
    message.success('地点已删除')
    await refreshAfterPlaceChange()
  } catch (error: any) {
    message.error(error?.message || '删除地点失败')
  }
}

const focusPlace = (place: Place) => {
  selectedPlaceId.value = place.id
  if (!map) return
  const lng = Number(place.location.longitude)
  const lat = Number(place.location.latitude)
  if (Number.isFinite(lng) && Number.isFinite(lat)) {
    try {
      map.setZoomAndCenter(15, [lng, lat])
    } catch {
      /* ignore */
    }
  }
}

const destroyCurrentMap = () => {
  clearCameraSyncTimer()
  cameraAnimating = false
  selectedMapDay.value = 'all'
  amapInstance = null
  amapRouteOverlays = []
  amapRouteLabels = []

  // 清理高德地图
  amapInfoWindows.forEach((infoWindow) => {
    try {
      infoWindow.close()
    } catch {
      /* ignore */
    }
  })
  amapInfoWindows = []
  amapMarkers = []
  if (map) {
    try {
      map.clearMap()
    } catch {
      /* ignore */
    }
    try { map.destroy() } catch {}
    map = null
  }
  mapLoading.value = false
}

// 数据变化（编辑保存、预算增删）只需重绘覆盖物，不再销毁 WebGL 实例：
// 反复 destroy + new AMap.Map 会造成 GPU 上下文与事件堆积，表现为 3D 地图越用越卡。
const invalidateMapData = () => {
  mapDirty = true
  if (map && activeSection.value === 'map') {
    mapDirty = false
    void refreshMap({ preserveCamera: true })
  }
}

const waitForMapLayout = () =>
  new Promise<void>((resolve) => {
    let done = false
    const finish = () => {
      if (done) return
      done = true
      resolve()
    }
    if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
      window.requestAnimationFrame(finish)
    }
    // 后台标签页里 rAF 可能不触发，加一个短的兜底
    window.setTimeout(finish, 120)
  })

const ensureMapReady = async () => {
  // 刷新流程会主动重建地图，避免这里再初始化一次造成竞态
  if (mapRefreshing.value) return
  await nextTick()
  await waitForMapLayout()
  if (mapProviderType.value === 'amap' && map && !mapUnhealthy) {
    if (typeof map.resize === 'function') {
      map.resize()
    }
    return
  }
  if (mapUnhealthy) {
    await refreshMap()
    return
  }
  // 都不存在则初始化
  await initMap()
}

const refreshMap = async (options: MapRenderOptions = {}) => {
  if (mapRefreshing.value) {
    mapRefreshQueued = true
    queuedMapRefreshOptions = options
    return
  }
  mapRefreshing.value = true
  try {
    // 地图容器在概览/预算分区下是 display:none，直接初始化会拿到 0 尺寸，
    // 导致 AMap 的 Pixel(NaN, NaN) / LngLat(NaN, NaN) 与“刷新失败”。
    // 先把地图分区切出来，等布局稳定后再操作。
    if (activeSection.value !== 'map') {
      activeSection.value = 'map'
      await nextTick()
    }
    await waitForMapLayout()

    // WebGL 上下文丢失时轻量刷新往往无法恢复，直接重建实例，给用户一个确定的恢复路径。
    const forceRebuild = mapUnhealthy
    if (forceRebuild) {
      console.warn('地图实例异常，执行完整重建')
      mapUnhealthy = false
    }

    // 已经有地图实例时只做轻量刷新：重算标记/路线并修正尺寸。
    // 这样既不会反复销毁 WebGL 实例造成卡顿，也避免加载器/Key 的重复请求。
    if (!forceRebuild && map && mapProviderType.value === 'amap' && amapInstance) {
      try {
        map.resize?.()
        await renderMapAttractions(amapInstance, options)
        message.success(t('result.messages.mapLoaded'))
        return
      } catch (lightError) {
        console.warn('地图轻量刷新失败，改为重建实例:', lightError)
        mapUnhealthy = true
      }
    }

    // 没有可用实例（首次进入或上一次初始化失败）时才完整重建
    mapInitGeneration += 1
    destroyCurrentMap()
    await nextTick()
    await waitForMapLayout()
    await initMap()
  } catch (error) {
    console.error('刷新地图失败:', error)
    message.error(t('result.messages.mapLoadFailed'))
  } finally {
    mapRefreshing.value = false
    if (mapRefreshQueued) {
      mapRefreshQueued = false
      const nextOptions = queuedMapRefreshOptions || {}
      queuedMapRefreshOptions = null
      void refreshMap(nextOptions)
    }
  }
}

const handleRuntimeSettingsUpdated = () => {
  destroyCurrentMap()
  if (activeSection.value === 'map') {
    void nextTick(async () => {
      await ensureMapReady()
    })
  }
}



onMounted(async () => {
  if (typeof window !== 'undefined') {
    window.addEventListener(RUNTIME_SETTINGS_UPDATED_EVENT, handleRuntimeSettingsUpdated)
  }
  try {
    tripFormMeta.value = JSON.parse(sessionStorage.getItem('tripFormMeta') || '{}') || {}
  } catch {
    tripFormMeta.value = {}
  }
  const storedPlanId = String(sessionStorage.getItem('planId') || '')
  planId.value = String(route.query.plan_id || storedPlanId || '')
  if (planId.value) {
    sessionStorage.setItem('planId', planId.value)
  }

  const cachedPlanId = storedPlanId
  const data = sessionStorage.getItem('tripPlan')
  const canUseCachedData = Boolean(data) && (!planId.value || !cachedPlanId || cachedPlanId === planId.value)

  if (data && canUseCachedData) {
    await applyTripPlanPayload({
      plan: JSON.parse(data),
      planId: planId.value || cachedPlanId,
    })
    return
  }

  if (planId.value) {
    try {
      const task = await pollTaskStatus(planId.value)
      if (task?.status === 'completed' && task.result) {
        const restored = await restoreTripPlanFromResponse(task.result)
        if (restored) return
      }
      if (task?.status === 'failed') {
        message.error(task.error || t('result.noTripPlanDesc'))
      }
    } catch (error) {
      console.error('结果页从后端回补旅行计划失败:', error)
    }
  }
})

watch(activeSection, async (section) => {
  if (!tripPlan.value) return
  if (section === 'map') {
    if (mapDirty) {
      mapDirty = false
      await refreshMap({ preserveCamera: true })
    } else {
      await ensureMapReady()
    }
    return
  }
  if (section === 'discover') {
    void loadPopularAttractions()
  }
})

watch(
  overviewAttractions,
  (items) => {
    if (overviewDetailItem.value) {
      const current = overviewDetailItem.value
      const stillExists = items.some(
        (item) =>
          item.dayArrayIndex === current.dayArrayIndex &&
          item.order === current.order &&
          item.name === current.name
      )
      if (!stillExists) closeOverviewDetail()
    }
  },
  { immediate: true }
)

onUnmounted(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener(RUNTIME_SETTINGS_UPDATED_EVENT, handleRuntimeSettingsUpdated)
  }
  destroyCurrentMap()

})

const goBack = () => {
  router.push('/')
}

// 滚动到指定区域
const scrollToSection = ({ key }: { key: string }) => {
  if (key.startsWith('day-')) {
    const dayIndex = Number(key.replace('day-', ''))
    if (!Number.isNaN(dayIndex)) {
      activeDays.value = [dayIndex]
      activeSection.value = 'days'
      return
    }
  }

  activeSection.value = key
}

const overviewGuideKey = (item: OverviewAttractionItem) =>
  `${item.dayArrayIndex}-${item.order}-${item.name}`

const scrollOverviewDetailIntoView = async () => {
  await nextTick()
  if (activeSection.value !== 'overview') return
  const element = document.getElementById('overview-attraction-detail')
  if (!element || !element.offsetParent) return
  const rect = element.getBoundingClientRect()
  // 面板在首屏下半部时向上让出阅读位置；已经在舒适区域则不打断当前滚动
  if (rect.top < 72 || rect.top > window.innerHeight * 0.45) {
    // 结果页的实际滚动容器是 window，显式计算目标位置，避免 scrollIntoView
    // 在 overflow-x:hidden 的嵌套容器里只滚动一小段。
    const target = window.scrollY + rect.top - 92
    window.scrollTo({ top: Math.max(0, target), behavior: 'smooth' })
  }
}

const loadOverviewGuide = async (item: OverviewAttractionItem, force = false) => {
  const key = overviewGuideKey(item)
  if (!force) {
    const cached = overviewGuideCache.get(key)
    if (cached) {
      overviewGuideRequestId += 1
      overviewGuide.value = cached
      overviewGuideError.value = ''
      overviewGuideLoading.value = false
      return
    }
  }

  const requestId = ++overviewGuideRequestId
  overviewGuideLoading.value = true
  overviewGuideError.value = ''
  if (force) overviewGuide.value = null

  try {
    const guide = await fetchAttractionGuide({
      name: item.name,
      city: tripPlan.value?.city || '',
      address: item.address,
      description: item.description,
      category: item.category,
    })
    if (requestId !== overviewGuideRequestId) return
    overviewGuide.value = guide
    overviewGuideCache.set(key, guide)
  } catch (error) {
    if (requestId !== overviewGuideRequestId) return
    console.error('加载景点导览失败:', error)
    overviewGuideError.value = t('result.attractionDetail.error')
  } finally {
    if (requestId === overviewGuideRequestId) {
      overviewGuideLoading.value = false
      // 等正文渲染完成后再定位，避免加载态变高时打断平滑滚动
      await nextTick()
      void scrollOverviewDetailIntoView()
    }
  }
}

// 预取：把行程前几张景点的导览提前生成，用户点「进入」时直接命中缓存，
// 避免每次首次打开都等一次完整 LLM 生成（实测 5–12s）。
const guidePrefetchInFlight = new Map<string, AbortController>()
let guidePrefetchGeneration = 0

const cancelGuidePrefetch = () => {
  guidePrefetchGeneration += 1
  for (const controller of guidePrefetchInFlight.values()) {
    controller.abort()
  }
  guidePrefetchInFlight.clear()
}

const prefetchOverviewGuide = async (item: OverviewAttractionItem) => {
  const key = overviewGuideKey(item)
  if (overviewGuideCache.has(key) || guidePrefetchInFlight.has(key)) return
  const controller = new AbortController()
  guidePrefetchInFlight.set(key, controller)
  try {
    const guide = await fetchAttractionGuide(
      {
        name: item.name,
        city: tripPlan.value?.city || '',
        address: item.address,
        description: item.description,
        category: item.category,
      },
      controller.signal
    )
    if (!overviewGuideCache.has(key)) overviewGuideCache.set(key, guide)
  } catch (error) {
    if ((error as Error)?.name !== 'AbortError') {
      console.debug('景点导览预取失败:', item.name, error)
    }
  } finally {
    guidePrefetchInFlight.delete(key)
  }
}

const prefetchOverviewGuides = () => {
  // 只预热首屏前 3 张；用户点开详情时会立即中止预取，把模型并发让给当前景点。
  const queue = overviewAttractions.value.slice(0, 3)
  if (queue.length === 0) return
  const generation = ++guidePrefetchGeneration
  void (async () => {
    for (const item of queue) {
      if (generation !== guidePrefetchGeneration) return
      await prefetchOverviewGuide(item)
    }
  })()
}

// 点击概览卡片中的「进入」：在当前位置展开景点详解，不跳转每日行程
const openOverviewDetail = (item: OverviewAttractionItem) => {
  cancelGuidePrefetch()
  const key = overviewGuideKey(item)
  if (overviewDetailItem.value && overviewGuideKey(overviewDetailItem.value) === key) {
    void scrollOverviewDetailIntoView()
    return
  }

  overviewDetailItem.value = item
  overviewGuide.value = null
  overviewGuideError.value = ''
  overviewGuideLoading.value = false

  const cached = overviewGuideCache.get(key)
  if (cached) {
    overviewGuideRequestId += 1
    overviewGuide.value = cached
    void scrollOverviewDetailIntoView()
  } else {
    void loadOverviewGuide(item)
  }
}

function closeOverviewDetail() {
  overviewGuideRequestId += 1
  overviewDetailItem.value = null
  overviewGuide.value = null
  overviewGuideError.value = ''
  overviewGuideLoading.value = false
}

const retryOverviewDetail = () => {
  if (!overviewDetailItem.value) return
  void loadOverviewGuide(overviewDetailItem.value, true)
}

// ===== 热门景点发现页：沿用概览景点详解的模板与导览接口 =====
const discoverGuideKey = (item: PopularAttraction) =>
  `popular:${item.city}:${item.name}`

const discoverDetailItem = computed<OverviewAttractionItem | null>(() => {
  const item = discoverDetail.value
  if (!item) return null
  return {
    name: item.name,
    address: item.address,
    visit_duration: item.visit_duration,
    description: item.description,
    category: item.category,
    ticket_price: item.ticket_price ?? undefined,
    dayNumber: discoverAddDay.value + 1,
    dayArrayIndex: discoverAddDay.value,
    order: 0,
  }
})

const discoverDetailImages = computed<string[]>(() => {
  const item = discoverDetail.value
  if (!item) return []
  const urls: string[] = []
  const add = (value?: string | null) => {
    const src = toProxiedPhotoUrl(value)
    if (src && !urls.includes(src)) urls.push(src)
  }
  add(item.image_url)
  for (const photo of item.photos || []) add(photo)
  return urls
})

const loadDiscoverGuide = async (item: PopularAttraction, force = false) => {
  const key = discoverGuideKey(item)
  if (!force) {
    const cached = discoverGuideCache.get(key)
    if (cached) {
      discoverGuideRequestId += 1
      discoverGuide.value = cached
      discoverGuideError.value = ''
      discoverGuideLoading.value = false
      return
    }
  }

  const requestId = ++discoverGuideRequestId
  discoverGuideLoading.value = true
  discoverGuideError.value = ''
  if (force) discoverGuide.value = null
  try {
    const guide = await fetchAttractionGuide({
      name: item.name,
      city: tripPlan.value?.city || item.city,
      address: item.address,
      description: item.description,
      category: item.category,
    })
    if (requestId !== discoverGuideRequestId) return
    discoverGuide.value = guide
    discoverGuideCache.set(key, guide)
  } catch (error) {
    if (requestId !== discoverGuideRequestId) return
    console.error('加载热门景点导览失败:', error)
    discoverGuideError.value = t('result.attractionDetail.error')
  } finally {
    if (requestId === discoverGuideRequestId) {
      discoverGuideLoading.value = false
    }
  }
}

const openDiscoverDetail = (item: PopularAttraction) => {
  discoverDetail.value = item
  discoverGuide.value = null
  discoverGuideError.value = ''
  discoverGuideLoading.value = false
  const cached = discoverGuideCache.get(discoverGuideKey(item))
  if (cached) {
    discoverGuide.value = cached
  } else {
    void loadDiscoverGuide(item)
  }
}

const closeDiscoverDetail = () => {
  discoverGuideRequestId += 1
  discoverDetail.value = null
  discoverGuide.value = null
  discoverGuideError.value = ''
  discoverGuideLoading.value = false
}

const retryDiscoverDetail = () => {
  if (!discoverDetail.value) return
  void loadDiscoverGuide(discoverDetail.value, true)
}

const loadPopularAttractions = async (force = false) => {
  const city = tripPlan.value?.city || ''
  if (!city) return
  if (popularLoading.value) return
  if (!force && popularLoadedCity.value === city && !popularError.value) return
  popularLoading.value = true
  popularError.value = ''
  try {
    popularAttractions.value = await fetchPopularAttractions(
      city,
      currentAttractionNames.value,
      12,
    )
    popularLoadedCity.value = city
  } catch (error: any) {
    popularError.value = error?.message || t('result.discover.loadFailed')
    popularAttractions.value = []
  } finally {
    popularLoading.value = false
  }
}

const openDiscoverPage = () => {
  activeSection.value = 'discover'
  discoverDetail.value = null
  if (discoverDayOptions.value.length) {
    discoverAddDay.value = Math.min(discoverAddDay.value, discoverDayOptions.value.length - 1)
  }
  void loadPopularAttractions()
}

const addPopularAttraction = async (item: PopularAttraction) => {
  if (!planId.value || discoverUpdating.value) return
  discoverUpdating.value = true
  discoverAddingId.value = item.id
  try {
    await createPlace(planId.value, {
      day_index: discoverAddDay.value,
      type: 'attraction',
      name: item.name,
      address: item.address,
      location: item.location,
      source: 'amap',
      amap_poi_id: item.id,
      note: item.description,
      visit_duration_min: item.visit_duration,
    })
    await refreshAfterPlaceChange({ openDrawer: false })
    popularAttractions.value = popularAttractions.value.filter(
      (candidate) => candidate.id !== item.id && candidate.name !== item.name,
    )
    popularLoadedCity.value = ''
    await loadPopularAttractions(true)
    if (discoverDetail.value?.id === item.id) closeDiscoverDetail()
    message.success(t('result.discover.added', { name: item.name }))
  } catch (error: any) {
    message.error(error?.message || t('result.discover.addFailed'))
  } finally {
    discoverAddingId.value = ''
    discoverUpdating.value = false
  }
}

// 切换编辑模式
const toggleEditMode = () => {
  editMode.value = true
  // 保存原始数据用于取消编辑
  originalPlan.value = JSON.parse(JSON.stringify(tripPlan.value))
  message.info(t('result.messages.enterEditMode'))
}

// 保存修改
const saveChanges = () => {
  editMode.value = false
  recalculateBudgetTotals()
  // 更新sessionStorage
  if (tripPlan.value) {
    sessionStorage.setItem('tripPlan', JSON.stringify(tripPlan.value))
  }
  message.success(t('result.messages.changesSaved'))

  // 重新绘制地图覆盖物以反映更改（不重建 WebGL 实例）
  invalidateMapData()
}

// 取消编辑
const cancelEdit = () => {
  if (originalPlan.value) {
    tripPlan.value = JSON.parse(JSON.stringify(originalPlan.value))
  }
  pendingBudgetItems.value = []
  mapPickMode.value = false
  editMode.value = false
  message.info(t('result.messages.editCanceled'))
  // 恢复原始行程后必须撤销编辑期间地图上的 marker/路线，否则会出现
  // “取消后地图仍是编辑中的状态”，再点 3D/刷新时叠加旧覆盖物。
  if (activeSection.value === 'map') {
    void refreshMap({ preserveCamera: true })
  }
}

// 删除景点
const deleteAttraction = (dayIndex: number, attrIndex: number) => {
  if (!tripPlan.value) return

  const day = tripPlan.value.days[dayIndex]
  if (day.attractions.length <= 1) {
    message.warning(t('result.messages.keepOneAttraction'))
    return
  }

  day.attractions.splice(attrIndex, 1)
  recalculateBudgetTotals()
  message.success(t('result.messages.attractionDeleted'))
}

// 移动景点顺序
const moveAttraction = (dayIndex: number, attrIndex: number, direction: 'up' | 'down') => {
  if (!tripPlan.value) return

  const day = tripPlan.value.days[dayIndex]
  const attractions = day.attractions

  if (direction === 'up' && attrIndex > 0) {
    [attractions[attrIndex], attractions[attrIndex - 1]] = [attractions[attrIndex - 1], attractions[attrIndex]]
  } else if (direction === 'down' && attrIndex < attractions.length - 1) {
    [attractions[attrIndex], attractions[attrIndex + 1]] = [attractions[attrIndex + 1], attractions[attrIndex]]
  }
}

const getMealLabel = (type: string): string => {
  const labels: Record<string, string> = {
    breakfast: t('result.meals.breakfast'),
    lunch: t('result.meals.lunch'),
    dinner: t('result.meals.dinner'),
    snack: t('result.meals.snack')
  }
  return labels[type] || type
}

const toBudgetNumber = (value: unknown): number => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric) || numeric <= 0) return 0
  return numeric
}

const roundBudgetAmount = (value: number): number => {
  return Math.round((value + Number.EPSILON) * 100) / 100
}

const formatBudgetAmount = (value: number): string => {
  const rounded = roundBudgetAmount(value)
  return new Intl.NumberFormat(localeTag.value, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 0,
  }).format(rounded)
}

const budgetIncludeInterCity = computed(() =>
  tripPlan.value?.budget?.include_inter_city_transport_in_budget !== false
)

const interCityTotal = computed(() =>
  roundBudgetAmount(toBudgetNumber(tripPlan.value?.budget?.total_inter_city_transport))
)

const interCityMode = computed(
  () => tripPlan.value?.budget?.intercity_transport_mode || tripFormMeta.value.intercity_transportation || ''
)

const SEAT_OPTIONS_BY_MODE: Record<string, string[]> = {
  高铁: ['二等座', '一等座', '特等座', '商务座', '无座'],
  火车: ['硬座', '软座', '硬卧', '软卧', '高级软卧', '无座'],
  飞机: ['经济舱', '超级经济舱', '公务舱', '头等舱'],
}

const interCitySeatLabel = computed(() => {
  if (!['高铁', '火车', '飞机'].includes(interCityMode.value)) return ''
  const fallback = interCityMode.value === '火车'
    ? '硬座'
    : interCityMode.value === '飞机'
      ? '经济舱'
      : '二等座'
  const stored = tripPlan.value?.budget?.intercity_seat_type || tripFormMeta.value.intercity_seat_type || ''
  const options = SEAT_OPTIONS_BY_MODE[interCityMode.value] || []
  return options.includes(stored) ? stored : fallback
})

const interCityPricingMeta = computed(() => {
  if (interCityTotal.value <= 0 || !interCityMode.value) return ''
  const budget = tripPlan.value?.budget
  const seat = interCitySeatLabel.value
  if (budget?.intercity_pricing_basis === '12306_distance_rule' && budget?.intercity_distance_km && seat) {
    return t('result.budget.intercityPricingNote', {
      mode: interCityMode.value,
      seat,
      amount: formatBudgetAmount(interCityTotal.value),
      distance: Math.round(Number(budget.intercity_distance_km) || 0),
    })
  }
  if (!seat) {
    return t('result.budget.intercityModeNote', { mode: interCityMode.value })
  }
  return t('result.budget.intercityLlmNote', {
    mode: interCityMode.value,
    seat,
  })
})

const budgetLimit = computed<number | null>(() => {
  const value = Number(tripPlan.value?.budget?.budget_limit)
  return Number.isFinite(value) && value > 0 ? value : null
})

const budgetOverAmount = computed(() => {
  if (budgetLimit.value === null) return 0
  return Math.max(0, roundBudgetAmount((tripPlan.value?.budget?.total ?? 0) - budgetLimit.value))
})

const budgetTotalLabel = computed(() =>
  budgetIncludeInterCity.value
    ? t('result.budget.totalWithIntercity')
    : t('result.budget.totalWithoutIntercity')
)

const ensureBudgetMetadata = () => {
  const budget = tripPlan.value?.budget
  if (!budget) return
  // 旧计划没有这个字段；旧版总额一直包含城际，按 legacy 规则兼容。
  if (budget.include_inter_city_transport_in_budget === undefined ||
      budget.include_inter_city_transport_in_budget === null) {
    budget.include_inter_city_transport_in_budget = true
  }
  if (budget.budget_limit === undefined) {
    budget.budget_limit = null
  }
}

const getBudgetTypeLabel = (type: BudgetItemType): string => {
  const labels: Record<BudgetItemType, string> = {
    attraction: t('result.budget.attraction'),
    hotel: t('result.budget.hotel'),
    meal: t('result.budget.meal'),
    transport: t('result.budget.transport'),
  }
  return labels[type]
}

const cloneData = <T>(data: T): T => JSON.parse(JSON.stringify(data)) as T

const recalculateBudgetTotals = (transportationOverride?: number) => {
  if (!tripPlan.value || !tripPlan.value.budget) return

  let attractionTotal = 0
  let hotelTotal = 0
  let mealTotal = 0

  tripPlan.value.days.forEach((day) => {
    day.attractions.forEach((attraction) => {
      attractionTotal += toBudgetNumber(attraction.ticket_price)
    })

    if (day.hotel) {
      hotelTotal += toBudgetNumber(day.hotel.estimated_cost)
    }

    day.meals.forEach((meal) => {
      mealTotal += toBudgetNumber(meal.estimated_cost)
    })
  })

  const transportationTotal = roundBudgetAmount(
    transportationOverride ?? toBudgetNumber(tripPlan.value.budget?.total_transportation)
  )
  // 城际交通是独立预算项，编辑市内金额/删除条目时不能被丢掉
  const interCityAmount = roundBudgetAmount(
    toBudgetNumber(tripPlan.value.budget?.total_inter_city_transport)
  )
  const includeInterCity =
    tripPlan.value.budget?.include_inter_city_transport_in_budget !== false
  const budgetLimitValue = tripPlan.value.budget?.budget_limit ?? null

  tripPlan.value.budget = {
    total_attractions: roundBudgetAmount(attractionTotal),
    total_hotels: roundBudgetAmount(hotelTotal),
    total_meals: roundBudgetAmount(mealTotal),
    total_transportation: transportationTotal,
    total_inter_city_transport: interCityAmount,
    total: roundBudgetAmount(
      attractionTotal + hotelTotal + mealTotal + transportationTotal +
      (includeInterCity ? interCityAmount : 0)
    ),
    include_inter_city_transport_in_budget: includeInterCity,
    budget_limit: budgetLimitValue,
    // 城际票价元数据与总预算分属不同口径，编辑其他金额时不能丢。
    intercity_transport_mode: tripPlan.value.budget?.intercity_transport_mode,
    intercity_seat_type: tripPlan.value.budget?.intercity_seat_type,
    intercity_distance_km: tripPlan.value.budget?.intercity_distance_km,
    intercity_ticket_total: tripPlan.value.budget?.intercity_ticket_total,
    intercity_pricing_basis: tripPlan.value.budget?.intercity_pricing_basis,
  }
}

const budgetItems = computed<BudgetDetailItem[]>(() => {
  if (!tripPlan.value) return []

  const items: BudgetDetailItem[] = []

  tripPlan.value.days.forEach((day, dayIndex) => {
    const dayNumber = dayIndex + 1

    day.attractions.forEach((attraction, attractionIndex) => {
      const amount = roundBudgetAmount(toBudgetNumber(attraction.ticket_price))
      if (amount <= 0) return
      items.push({
        id: `attraction-${dayIndex}-${attractionIndex}`,
        type: 'attraction',
        dayIndex,
        dayNumber,
        name: attraction.name,
        amount,
        sourceIndex: attractionIndex,
      })
    })

    if (day.hotel) {
      const amount = roundBudgetAmount(toBudgetNumber(day.hotel.estimated_cost))
      if (amount > 0) {
        items.push({
          id: `hotel-${dayIndex}`,
          type: 'hotel',
          dayIndex,
          dayNumber,
          name: day.hotel.name,
          amount,
        })
      }
    }

    day.meals.forEach((meal, mealIndex) => {
      const amount = roundBudgetAmount(toBudgetNumber(meal.estimated_cost))
      if (amount <= 0) return
      items.push({
        id: `meal-${dayIndex}-${mealIndex}`,
        type: 'meal',
        dayIndex,
        dayNumber,
        name: `${getMealLabel(meal.type)} · ${meal.name}`,
        amount,
        sourceIndex: mealIndex,
      })
    })
  })

  const transportTotal = roundBudgetAmount(toBudgetNumber(tripPlan.value.budget?.total_transportation))
  const transportDays = tripPlan.value.days
    .map((day, dayIndex) => ({ day, dayIndex }))
    .filter(({ day }) => Boolean(day.transportation && day.transportation.trim()))

  if (transportTotal > 0 && transportDays.length > 0) {
    const avg = roundBudgetAmount(transportTotal / transportDays.length)
    let remaining = transportTotal

    transportDays.forEach(({ day, dayIndex }, index) => {
      const amount = index === transportDays.length - 1 ? remaining : Math.min(avg, remaining)
      remaining = roundBudgetAmount(remaining - amount)
      items.push({
        id: `transport-${dayIndex}`,
        type: 'transport',
        dayIndex,
        dayNumber: day.day_index + 1,
        name: day.transportation,
        amount: roundBudgetAmount(amount),
      })
    })
  }

  return items
})

const budgetPlayRank = (item: BudgetDetailItem): number => {
  const sourceIndex = item.sourceIndex ?? 0
  switch (item.type) {
    case 'transport':
      return 0
    case 'attraction':
      return 10 + sourceIndex
    case 'meal':
      return 100 + sourceIndex
    case 'hotel':
      return 200
    default:
      return 999
  }
}

watch(
  budgetItems,
  (items) => {
    if (budgetCustomOrder.value.length === 0) {
      budgetCustomOrder.value = [...items]
        .sort(
          (a, b) =>
            (a.dayNumber ?? 0) - (b.dayNumber ?? 0) || budgetPlayRank(a) - budgetPlayRank(b)
        )
        .map((item) => item.id)
      return
    }

    const ids = new Set(items.map((item) => item.id))
    const next = budgetCustomOrder.value.filter((id) => ids.has(id))
    const known = new Set(next)
    for (const item of items) {
      if (!known.has(item.id)) {
        next.push(item.id)
        known.add(item.id)
      }
    }
    budgetCustomOrder.value = next
  },
  { immediate: true }
)

const filteredBudgetItems = computed<BudgetDetailItem[]>(() => {
  let items = budgetItems.value

  if (budgetFilterType.value !== 'all') {
    items = items.filter((item) => item.type === budgetFilterType.value)
  }
  if (budgetFilterDay.value !== 'all') {
    items = items.filter((item) => item.dayIndex === budgetFilterDay.value)
  }

  const sorted = [...items]
  sorted.sort((a, b) => {
    const dayA = a.dayNumber ?? Number.MAX_SAFE_INTEGER
    const dayB = b.dayNumber ?? Number.MAX_SAFE_INTEGER

    switch (budgetSortMode.value) {
      case 'amountAsc':
        return a.amount - b.amount
      case 'dayAsc':
        return dayA - dayB || b.amount - a.amount
      case 'dayDesc':
        return dayB - dayA || b.amount - a.amount
      case 'custom': {
        const order = new Map(budgetCustomOrder.value.map((id, index) => [id, index]))
        return (
          (order.get(a.id) ?? Number.MAX_SAFE_INTEGER) -
          (order.get(b.id) ?? Number.MAX_SAFE_INTEGER)
        )
      }
      case 'playOrder':
        return dayA - dayB || budgetPlayRank(a) - budgetPlayRank(b)
      case 'amountDesc':
      default:
        return b.amount - a.amount
    }
  })

  return sorted
})

const filteredBudgetTotal = computed(() =>
  roundBudgetAmount(
    filteredBudgetItems.value.reduce((sum, item) => sum + toBudgetNumber(item.amount), 0)
  )
)

const budgetFilterDayLabel = computed(() =>
  budgetFilterDay.value === 'all'
    ? t('result.budget.allDays')
    : t('common.dayNumber', { day: budgetFilterDay.value + 1 })
)

const resetBudgetOrder = () => {
  const ordered = [...budgetItems.value].sort(
    (a, b) => (a.dayNumber ?? 0) - (b.dayNumber ?? 0) || budgetPlayRank(a) - budgetPlayRank(b)
  )
  budgetCustomOrder.value = ordered.map((item) => item.id)
  budgetSortMode.value = 'playOrder'
}

const canMoveBudgetItem = (item: BudgetDetailItem, direction: -1 | 1): boolean => {
  const items = filteredBudgetItems.value
  const currentIndex = items.findIndex((candidate) => candidate.id === item.id)
  if (currentIndex < 0) return false
  let targetIndex = currentIndex + direction
  while (targetIndex >= 0 && targetIndex < items.length) {
    if (items[targetIndex].dayIndex === item.dayIndex) return true
    targetIndex += direction
  }
  return false
}

const moveBudgetItem = (item: BudgetDetailItem, direction: -1 | 1) => {
  const items = filteredBudgetItems.value
  const currentIndex = items.findIndex((candidate) => candidate.id === item.id)
  if (currentIndex < 0) return

  let targetIndex = currentIndex + direction
  while (targetIndex >= 0 && targetIndex < items.length) {
    if (items[targetIndex].dayIndex === item.dayIndex) break
    targetIndex += direction
  }
  if (targetIndex < 0 || targetIndex >= items.length) return

  const target = items[targetIndex]
  const order = [...budgetCustomOrder.value]
  const from = order.indexOf(item.id)
  const to = order.indexOf(target.id)
  if (from < 0 || to < 0) return
  ;[order[from], order[to]] = [order[to], order[from]]
  budgetCustomOrder.value = order
  // 手动调换后自动进入自定义排序，后续上/下移都基于当前顺序
  budgetSortMode.value = 'custom'
}

const applyBudgetAmount = (item: BudgetDetailItem, nextAmount: number): boolean => {
  if (!tripPlan.value || item.dayIndex === null) return false

  const day = tripPlan.value.days[item.dayIndex]
  if (!day) return false

  let changed = false

  if (item.type === 'attraction' && typeof item.sourceIndex === 'number' && day.attractions[item.sourceIndex]) {
    day.attractions[item.sourceIndex].ticket_price = nextAmount
    changed = true
  }

  if (item.type === 'meal' && typeof item.sourceIndex === 'number' && day.meals[item.sourceIndex]) {
    day.meals[item.sourceIndex].estimated_cost = nextAmount
    changed = true
  }

  if (item.type === 'hotel' && day.hotel) {
    day.hotel.estimated_cost = nextAmount
    changed = true
  }

  const transportationTotal =
    item.type === 'transport'
      ? Math.max(
          0,
          roundBudgetAmount(toBudgetNumber(tripPlan.value.budget?.total_transportation) - item.amount + nextAmount)
        )
      : undefined

  if (item.type === 'transport' && day.transportation && day.transportation.trim()) {
    changed = true
  }

  if (!changed) return false

  const budget = tripPlan.value.budget
  if (budget) {
    // 只按本次修改的差额调整对应分类，保留城际交通与其他分类原值，
    // 避免改一个景点后整张预算表被重算导致总额突然跳变。
    const delta = roundBudgetAmount(nextAmount - item.amount)
    if (item.type === 'attraction') {
      budget.total_attractions = Math.max(0, roundBudgetAmount(budget.total_attractions + delta))
    } else if (item.type === 'meal') {
      budget.total_meals = Math.max(0, roundBudgetAmount(budget.total_meals + delta))
    } else if (item.type === 'hotel') {
      budget.total_hotels = Math.max(0, roundBudgetAmount(budget.total_hotels + delta))
    } else if (item.type === 'transport' && transportationTotal !== undefined) {
      budget.total_transportation = transportationTotal
    }
    budget.total = Math.max(0, roundBudgetAmount(budget.total + delta))
  } else {
    recalculateBudgetTotals(transportationTotal)
  }

  sessionStorage.setItem('tripPlan', JSON.stringify(tripPlan.value))
  return true
}

const startBudgetEdit = (item: BudgetDetailItem) => {
  editingBudgetId.value = item.id
  budgetEditDraft.value = item.amount
}

const cancelBudgetEdit = () => {
  editingBudgetId.value = ''
  budgetEditDraft.value = 0
}

const saveBudgetEdit = (item: BudgetDetailItem) => {
  const numeric = Number(budgetEditDraft.value)
  if (!Number.isFinite(numeric) || numeric < 0) {
    message.warning(t('result.messages.budgetInvalidAmount'))
    return
  }

  const nextAmount = roundBudgetAmount(numeric)
  if (nextAmount === roundBudgetAmount(item.amount)) {
    cancelBudgetEdit()
    return
  }

  if (!applyBudgetAmount(item, nextAmount)) return
  cancelBudgetEdit()
  message.success(t('result.messages.budgetAmountUpdated'))
}

const deleteBudgetItem = (item: BudgetDetailItem) => {
  if (!tripPlan.value || item.dayIndex === null) return

  const day = tripPlan.value.days[item.dayIndex]
  if (!day) return

  let changed = false
  let restorePayload: BudgetRestorePayload | null = null

  if (item.type === 'attraction' && typeof item.sourceIndex === 'number') {
    const attraction = day.attractions[item.sourceIndex]
    if (attraction) {
      restorePayload = {
        type: 'attraction',
        attraction: cloneData(attraction),
        insertIndex: item.sourceIndex,
      }
      day.attractions.splice(item.sourceIndex, 1)
      changed = true
    }
  }

  if (item.type === 'meal' && typeof item.sourceIndex === 'number') {
    const meal = day.meals[item.sourceIndex]
    if (meal) {
      restorePayload = {
        type: 'meal',
        meal: cloneData(meal),
        insertIndex: item.sourceIndex,
      }
      day.meals.splice(item.sourceIndex, 1)
      changed = true
    }
  }

  if (item.type === 'hotel') {
    if (day.hotel) {
      restorePayload = {
        type: 'hotel',
        hotel: cloneData(day.hotel),
        accommodation: day.accommodation || '',
      }
      day.hotel = undefined
      day.accommodation = ''
      changed = true
    }
  }

  if (item.type === 'transport') {
    if (day.transportation && day.transportation.trim()) {
      restorePayload = {
        type: 'transport',
        transportation: day.transportation,
      }
      day.transportation = ''
      changed = true
    }
  }

  if (!changed || !restorePayload) return

  pendingBudgetItems.value.unshift({
    uid: `${item.id}-${Date.now()}`,
    base: cloneData(item),
    payload: restorePayload,
  })

  const transportationTotal =
    item.type === 'transport'
      ? Math.max(
          0,
          roundBudgetAmount(
            toBudgetNumber(tripPlan.value.budget?.total_transportation) - roundBudgetAmount(item.amount)
          )
        )
      : undefined

  recalculateBudgetTotals(transportationTotal)
  sessionStorage.setItem('tripPlan', JSON.stringify(tripPlan.value))

  invalidateMapData()

  message.success(t('result.messages.budgetItemDeleted'))
}

const restoreBudgetItem = (pendingItem: BudgetRestoreItem) => {
  if (!tripPlan.value || pendingItem.base.dayIndex === null) return

  const day = tripPlan.value.days[pendingItem.base.dayIndex]
  if (!day) return

  let changed = false

  if (pendingItem.payload.type === 'attraction') {
    const insertAt = Math.max(0, Math.min(pendingItem.payload.insertIndex, day.attractions.length))
    day.attractions.splice(insertAt, 0, cloneData(pendingItem.payload.attraction))
    changed = true
  }

  if (pendingItem.payload.type === 'meal') {
    const insertAt = Math.max(0, Math.min(pendingItem.payload.insertIndex, day.meals.length))
    day.meals.splice(insertAt, 0, cloneData(pendingItem.payload.meal))
    changed = true
  }

  if (pendingItem.payload.type === 'hotel') {
    day.hotel = cloneData(pendingItem.payload.hotel)
    day.accommodation = pendingItem.payload.accommodation
    changed = true
  }

  if (pendingItem.payload.type === 'transport') {
    day.transportation = pendingItem.payload.transportation
    changed = true
  }

  if (!changed) return

  const transportationTotal =
    pendingItem.base.type === 'transport'
      ? roundBudgetAmount(toBudgetNumber(tripPlan.value.budget?.total_transportation) + pendingItem.base.amount)
      : undefined

  recalculateBudgetTotals(transportationTotal)
  pendingBudgetItems.value = pendingBudgetItems.value.filter((item) => item.uid !== pendingItem.uid)
  sessionStorage.setItem('tripPlan', JSON.stringify(tripPlan.value))

  invalidateMapData()

  message.success(t('result.messages.budgetItemRestored'))
}

// 将小红书图片直链包装为后端代理地址，规避图片 CDN 的 Referer 防盗链（issue #28）
const toProxiedPhotoUrl = (url?: string | null): string => {
  if (!url) return ''
  return `${getRuntimeApiBaseUrl()}/api/poi/image?url=${encodeURIComponent(url)}`
}

// 展示用图片地址：高德图床允许浏览器直连且带 CORS 响应头，直连可省掉一次
// 后端中转；小红书直链必须走后端代理，否则会因防盗链/时效签名 403。
const toDisplayPhotoUrl = (url?: string | null): string => {
  const value = String(url || '').trim()
  if (!value) return ''
  if (value.startsWith('data:')) return value
  if (/autonavi\.com|amap\.com/i.test(value)) return value.replace(/^http:\/\//i, 'https://')
  return toProxiedPhotoUrl(value)
}

// 导出时图片必须是同源（html2canvas 受 CORS 限制）；高德图库直链统一改走后端代理
const toExportablePhotoUrl = (url?: string | null): string => {
  const value = String(url || '').trim()
  if (!value) return ''
  if (value.startsWith('data:') || value.includes('/api/poi/image?')) return value
  if (/autonavi\.com|amap\.com/i.test(value)) return toProxiedPhotoUrl(value)
  return value.startsWith('http') ? toProxiedPhotoUrl(value) : value
}

// 加载所有景点图片
const loadAttractionPhotos = async () => {
  if (!tripPlan.value) return

  const apiBase = getRuntimeApiBaseUrl()
  const city = tripPlan.value.city
  const uniqueNames = Array.from(
    new Set(
      tripPlan.value.days.flatMap((day) => day.attractions.map((attraction) => attraction.name))
    )
  ).filter((name) => name && !attractionPhotos.value[name])

  if (uniqueNames.length === 0) return

  const concurrencyLimit = 4
  let currentIndex = 0

  const loadNextPhoto = async () => {
    while (currentIndex < uniqueNames.length) {
      const index = currentIndex
      currentIndex += 1
      const name = uniqueNames[index]

      try {
        // 优先用高德 POI 实拍图：3 张、名称匹配、可按城市消歧，
        // 比小红书搜索首图更稳定，也避免出现与景点无关的图片。
        const galleryResponse = await fetch(
          `${apiBase}/api/poi/gallery?name=${encodeURIComponent(name)}&city=${encodeURIComponent(city)}&limit=3`
        )
        if (galleryResponse.ok) {
          const gallery = await galleryResponse.json()
          const photos = Array.isArray(gallery?.data?.photos)
            ? gallery.data.photos.filter((src: unknown) => typeof src === 'string' && src)
            : []
          if (photos.length > 0) {
            attractionPhotoGalleries.value[name] = photos
            // 卡片用缩略图 URL，详情大图用原图，兼顾清晰度与首屏流量
            attractionPhotos.value[name] = String(photos[0])
              .replace(/[?&]type=pic(?=&|$)/, '')
              .replace(/[?&]$/, '')
            continue
          }
        }

        // 高德无图时退回小红书 name 代理，保持旧行为
        const response = await fetch(
          `${apiBase}/api/poi/photo?name=${encodeURIComponent(name)}&city=${encodeURIComponent(city)}`
        )
        const data = await response.json()
        if (data.success && data.data.photo_url) {
          // 直链带时效签名会过期，统一改走后端 name 键代理（缓存 miss 时自动重搜重取）
          const proxied = `${apiBase}/api/poi/image?name=${encodeURIComponent(name)}`
          attractionPhotoGalleries.value[name] = [proxied]
          attractionPhotos.value[name] = proxied
        }
      } catch (err) {
        console.error(`获取${name}图片失败:`, err)
      }
    }
  }

  const workers = Array.from(
    { length: Math.min(concurrencyLimit, uniqueNames.length) },
    () => loadNextPhoto()
  )
  await Promise.all(workers)
}

// 统一的占位图（自带图标 + 景点名 + 提示），不依赖任何网络请求
const escapeSvgText = (value: string): string =>
  value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')

const buildImagePlaceholder = (name: string, hint: string): string => {
  const label = escapeSvgText((name || '').slice(0, 18))
  const note = escapeSvgText(hint || '')
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480" viewBox="0 0 640 480">
  <rect width="640" height="480" fill="#1a262f"/>
  <g fill="none" stroke="#4a6472" stroke-width="6" stroke-linecap="round" stroke-linejoin="round">
    <rect x="250" y="150" width="140" height="110" rx="12"/>
    <circle cx="290" cy="188" r="14"/>
    <path d="M258 246l44-40 32 28 22-18 26 30"/>
  </g>
  <text x="320" y="320" text-anchor="middle" font-family="Microsoft YaHei, Noto Sans SC, sans-serif" font-size="26" fill="#c8d6df">${label}</text>
  <text x="320" y="356" text-anchor="middle" font-family="Microsoft YaHei, Noto Sans SC, sans-serif" font-size="16" fill="#7c93a1">${note}</text>
</svg>`
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
}

// 获取景点图片
const getAttractionImage = (name: string, _index: number): string => {
  if (attractionPhotos.value[name]) {
    return attractionPhotos.value[name]
  }
  return buildImagePlaceholder(name, t('result.imagePlaceholder'))
}

// 图片加载失败：先对 name 代理强制重取一次，仍失败则降级为本地占位图
const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement | null
  if (!img) return
  const src = img.getAttribute('src') || ''
  // 高德图床偶发超时/防盗链时，改走后端代理（服务端已支持高德图片）。
  if (/autonavi\.com|amap\.com/i.test(src) && img.dataset.proxyFallback !== '1') {
    img.dataset.proxyFallback = '1'
    img.src = toProxiedPhotoUrl(src)
    return
  }
  const isNameProxy = src.includes('/api/poi/image?') && src.includes('name=')
  if (isNameProxy && img.dataset.retried !== '1') {
    img.dataset.retried = '1'
    img.src = `${src}&refresh=1`
    return
  }
  if (img.dataset.fallback === '1') return
  img.dataset.fallback = '1'
  img.src = buildImagePlaceholder(img.alt || '', t('result.imageLoadFailed'))
}



// ========== 构建导出用的纯净 HTML ==========
const buildExportHTML = (mapDataUrl: string = ''): string => {
  if (!tripPlan.value) return ''
  const tp = tripPlan.value as TripPlan & {
    hotel_recommendations?: Array<{
      name?: string
      price?: number | string
      address?: string
    }>
  }

  const mealLabels: Record<string, string> = {
    breakfast: t('result.meals.breakfast'),
    lunch: t('result.meals.lunch'),
    dinner: t('result.meals.dinner'),
    snack: t('result.meals.snack'),
  }

  // 每日行程 HTML
  let daysHTML = ''
  tp.days.forEach((day, index) => {
    let attractionsHTML = ''
    day.attractions.forEach((a, ai) => {
      const photoUrl =
        toExportablePhotoUrl(a.image_url) ||
        toExportablePhotoUrl(attractionPhotos.value[a.name]) ||
        ''
      const durationText = t('result.export.durationLine', { duration: a.visit_duration || '—' })
      // 图片自适应：不压缩不裁剪，保持原始比例
      const imgTag = photoUrl
        ? `<img src="${photoUrl}" style="width:100%;height:auto;max-height:400px;object-fit:contain;border-radius:8px;margin-bottom:8px;" crossorigin="anonymous" />`
        : `<div style="width:100%;height:80px;background:linear-gradient(135deg,#667eea,#764ba2);border-radius:8px;margin-bottom:8px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:18px;font-weight:bold;">${a.name}</div>`
      attractionsHTML += `
        <div style="flex:0 0 48%;background:#fff;border-radius:10px;padding:14px;box-shadow:0 2px 8px rgba(0,0,0,0.07);margin-bottom:14px;">
          ${imgTag}
          <h4 style="margin:0 0 6px;font-size:17px;color:#1a1a1a;">${ai + 1}. ${a.name}</h4>
          <p style="margin:2px 0;font-size:14px;color:#555;">${a.address || '—'}</p>
          <p style="margin:2px 0;font-size:14px;color:#555;">${durationText}${a.ticket_price ? `  |  ¥${a.ticket_price}（${t('result.referenceOnly')}）` : ''}</p>
          <p style="margin:4px 0;font-size:14px;color:#666;">${a.description || ''}</p>
        </div>`
    })

    // 餐饮推荐
    let mealsHTML = ''
    if (day.meals && day.meals.length) {
      mealsHTML = `<div style="margin-top:10px;"><strong style="color:#333;">${t('result.export.mealTitle')}</strong><div style="display:flex;flex-wrap:wrap;gap:10px;margin-top:6px;">`
      day.meals.forEach(m => {
        mealsHTML += `<div style="background:#fffbe6;padding:8px 14px;border-radius:8px;font-size:12px;color:#333;"><b>${mealLabels[m.type] || m.type}</b>: ${m.name || t('result.export.noMealRecommendation')}${m.estimated_cost ? ` (¥${m.estimated_cost}，${t('result.referenceOnly')})` : ''}</div>`
      })
      mealsHTML += '</div></div>'
    }

    // 当日高德路线：与地图同源的逐段摘要（交通方式 + 约耗时 + 距离）
    const dayLegs = [...(dayRouteLegs.get(index) || [])].sort((a, b) => a.order - b.order)
    let routeHTML = ''
    if (dayLegs.length) {
      const rows = dayLegs
        .map((leg, legIndex) => {
          const durationText = formatDurationText(leg.durationSec, leg.distanceM, leg.mode)
          const distanceText = leg.distanceM > 0 ? ` · ${(leg.distanceM / 1000).toFixed(1)} km` : ''
          return `<div style="display:flex;align-items:center;gap:8px;background:#f5f7fa;border-radius:8px;padding:8px 12px;font-size:13px;color:#333;margin-bottom:6px;">
            <span style="flex:0 0 auto;width:20px;height:20px;border-radius:50%;background:#0F6B4F;color:#ffffff;font-size:11px;display:flex;align-items:center;justify-content:center;">${legIndex + 1}</span>
            <span style="flex:1;min-width:0;">${leg.from} → ${leg.to}</span>
            <span style="flex:0 0 auto;color:#0F6B4F;font-weight:600;">${MODE_LABELS[leg.mode]} · 约${durationText}${distanceText}</span>
          </div>`
        })
        .join('')
      routeHTML = `<div style="margin-top:14px;padding-top:12px;border-top:1px dashed #e2dfd5;">
        <div style="font-size:14px;font-weight:700;color:#333;margin-bottom:8px;">${t('result.export.routeTitle')}</div>
        ${rows}
      </div>`
    }

    daysHTML += `
      <div style="background:#ffffff;border-radius:14px;padding:20px;margin-bottom:18px;box-shadow:0 2px 10px rgba(0,0,0,0.06);">
        <h3 style="margin:0 0 14px;color:#667eea;font-size:18px;">${t('result.export.dayTitle', { day: index + 1 })} <span style="font-size:14px;color:#888;margin-left:8px;">${day.date || ''}</span></h3>
        <div style="display:flex;flex-wrap:wrap;gap:12px;">
          ${attractionsHTML}
        </div>
        ${mealsHTML}
        ${routeHTML}
      </div>`
  })

  // 预算 HTML
  let budgetHTML = ''
  if (tp.budget) {
    const b = tp.budget
    const includeIntercity = b.include_inter_city_transport_in_budget !== false
    const intercityAmount = Number(b.total_inter_city_transport) || 0
    const budgetLimitValue = Number(b.budget_limit) || 0
    const overAmount = budgetLimitValue > 0 ? Math.max(0, Number(b.total || 0) - budgetLimitValue) : 0
    const intercityCard = intercityAmount > 0
      ? `<div style="flex:1;min-width:120px;background:#f5f7fa;padding:14px;border-radius:10px;text-align:center;">
           <div style="font-size:12px;color:#888;">${includeIntercity ? t('result.budget.intercityIncluded') : t('result.budget.intercityExcluded')}</div>
           <div style="font-size:20px;font-weight:bold;color:#333;">¥${intercityAmount}</div>
         </div>`
      : ''
    const limitBar = budgetLimitValue > 0
      ? `<div style="margin-bottom:12px;font-size:13px;color:${overAmount > 0 ? '#A83B2B' : '#0F6B4F'};">
           ${t('result.budget.limitLabel')} ¥${budgetLimitValue} ·
           ${overAmount > 0 ? t('result.budget.overBudget', { amount: overAmount }) : t('result.budget.withinBudget')}
         </div>`
      : ''
    const intercityNote = intercityAmount > 0 && !includeIntercity
      ? `<div style="margin-top:10px;font-size:12px;color:#6B756E;">${t('result.budget.intercityExcludeNote', { amount: intercityAmount })}</div>`
      : ''
    const intercityMeta = intercityAmount > 0 && interCityPricingMeta.value
      ? `<div style="margin-top:10px;font-size:12px;color:#6B756E;">${interCityPricingMeta.value}</div>`
      : ''
    budgetHTML = `
      <div style="background:#ffffff;border-radius:14px;padding:20px;margin-bottom:18px;box-shadow:0 2px 10px rgba(0,0,0,0.06);">
        <h3 style="margin:0 0 6px;color:#667eea;">${t('result.budget.title')}</h3>
        <div style="margin:0 0 12px;color:#6B756E;font-size:12px;line-height:1.5;">${t('result.budget.referenceNote')}</div>
        ${limitBar}
        <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:14px;">
          <div style="flex:1;min-width:120px;background:#f5f7fa;padding:14px;border-radius:10px;text-align:center;">
            <div style="font-size:12px;color:#888;">${t('result.budget.attraction')}</div><div style="font-size:20px;font-weight:bold;color:#333;">¥${b.total_attractions || 0}</div>
          </div>
          <div style="flex:1;min-width:120px;background:#f5f7fa;padding:14px;border-radius:10px;text-align:center;">
            <div style="font-size:12px;color:#888;">${t('result.budget.hotel')}</div><div style="font-size:20px;font-weight:bold;color:#333;">¥${b.total_hotels || 0}</div>
          </div>
          <div style="flex:1;min-width:120px;background:#f5f7fa;padding:14px;border-radius:10px;text-align:center;">
            <div style="font-size:12px;color:#888;">${t('result.budget.meal')}</div><div style="font-size:20px;font-weight:bold;color:#333;">¥${b.total_meals || 0}</div>
          </div>
          <div style="flex:1;min-width:120px;background:#f5f7fa;padding:14px;border-radius:10px;text-align:center;">
            <div style="font-size:12px;color:#888;">${t('result.budget.transport')}</div><div style="font-size:20px;font-weight:bold;color:#333;">¥${b.total_transportation || 0}</div>
          </div>
          ${intercityCard}
        </div>
        <div style="background:#667eea;color:#fff;padding:16px 20px;border-radius:12px;display:flex;justify-content:space-between;align-items:center;">
          <span style="font-size:16px;">${includeIntercity ? t('result.budget.totalWithIntercity') : t('result.budget.totalWithoutIntercity')}</span>
          <span style="font-size:26px;font-weight:bold;">¥${b.total || 0}</span>
        </div>
        ${intercityNote}
        ${intercityMeta}
      </div>`
  }

  // 地图截图 HTML
  let mapHTML = ''
  if (mapDataUrl) {
    mapHTML = `
      <div style="background:#ffffff;border-radius:14px;padding:20px;margin-bottom:18px;box-shadow:0 2px 10px rgba(0,0,0,0.06);">
        <h3 style="margin:0 0 14px;color:#667eea;">${t('result.side.map')}</h3>
        <img src="${mapDataUrl}" style="width:100%;height:auto;border-radius:10px;" />
      </div>`
  }

  // 天气 HTML
  let weatherHTML = ''
  if (tp.weather_info) {
    if (Array.isArray(tp.weather_info) && tp.weather_info.length > 0) {
      let weatherCards = ''
      tp.weather_info.forEach((w: any) => {
        weatherCards += `
          <div style="flex:1;min-width:180px;background:#2b2d3c;padding:16px;border-radius:12px;margin:5px;">
            <div style="text-align:center;color:#00e5ff;font-weight:bold;margin-bottom:12px;font-size:15px;">${w.date}</div>
            <div style="display:flex;align-items:center;margin-bottom:10px;">
              <div style="line-height:1.2;">
                <div style="font-size:12px;color:#99b0c9;margin-bottom:2px;">${t('result.export.daytime')}</div>
                <div style="font-size:14px;color:#fff;font-weight:600;">${w.day_weather} ${w.day_temp}°C</div>
              </div>
            </div>
            <div style="display:flex;align-items:center;margin-bottom:12px;">
              <div style="line-height:1.2;">
                <div style="font-size:12px;color:#99b0c9;margin-bottom:2px;">${t('result.export.nighttime')}</div>
                <div style="font-size:14px;color:#fff;font-weight:600;">${w.night_weather} ${w.night_temp}°C</div>
              </div>
            </div>
            <div style="border-top:1px solid rgba(255,255,255,0.1);padding-top:10px;text-align:center;font-size:12px;color:#99b0c9;">
              ${w.wind_direction} ${w.wind_power}
            </div>
          </div>`
      })
      weatherHTML = `
        <div style="background:#ffffff;border-radius:14px;padding:20px;margin-bottom:18px;box-shadow:0 2px 10px rgba(0,0,0,0.06);">
          <h3 style="margin:0 0 14px;color:#667eea;">${t('result.export.weatherTitle')}</h3>
          <div style="display:flex;flex-wrap:wrap;gap:10px;">
            ${weatherCards}
          </div>
        </div>`
    } else {
      weatherHTML = `
        <div style="background:#ffffff;border-radius:14px;padding:20px;margin-bottom:18px;box-shadow:0 2px 10px rgba(0,0,0,0.06);">
          <h3 style="margin:0 0 10px;color:#667eea;">${t('result.export.weatherTitle')}</h3>
          <p style="font-size:14px;color:#333;line-height:1.8;">${typeof tp.weather_info === 'string' ? tp.weather_info : JSON.stringify(tp.weather_info)}</p>
        </div>`
    }
  }

  // 酒店 HTML
  let hotelHTML = ''
  if (tp.hotel_recommendations && tp.hotel_recommendations.length) {
    let hotelItems = ''
    tp.hotel_recommendations.forEach((h) => {
      hotelItems += `<div style="background:#e3f2fd;padding:12px 16px;border-radius:10px;margin-bottom:8px;">
        <b style="color:#1565c0;">${h.name || t('result.export.hotelFallback')}</b>
        ${h.price ? `<span style="float:right;color:#e65100;font-weight:bold;">¥${h.price}${t('result.export.perNight')}</span>` : ''}
        ${h.address ? `<p style="margin:4px 0 0;font-size:12px;color:#555;">${h.address}</p>` : ''}
      </div>`
    })
    hotelHTML = `
      <div style="background:#ffffff;border-radius:14px;padding:20px;margin-bottom:18px;box-shadow:0 2px 10px rgba(0,0,0,0.06);">
        <h3 style="margin:0 0 14px;color:#1976d2;">${t('result.hotelTitle')}</h3>
        ${hotelItems}
      </div>`
  }

  // 页脚：个人版品牌，不含仓库链接/二维码
  const footerHTML = `
    <div style="text-align:center;padding:24px 16px 16px;border-top:1px solid #e8e8e8;margin-top:8px;">
      <div style="font-size:13px;color:#0F6B4F;font-weight:600;margin-bottom:4px;">远行 Farway</div>
      <div style="font-size:11px;color:#8a938c;">${t('result.export.footer')}</div>
    </div>`

  return `
    <div style="width:800px;padding:30px;background:#f0f2f5;font-family:'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;color:#333;">
      <div style="text-align:center;margin-bottom:24px;">
        <h1 style="margin:0;font-size:28px;color:#333;">${t('result.export.title', { city: tp.city })}</h1>
        <p style="margin:6px 0 0;font-size:14px;color:#888;">${t('result.export.subtitle', {
          start: tp.start_date || '',
          end: tp.end_date || '',
          days: tp.days?.length || 0,
        })}</p>
        ${tp.overall_suggestions ? `<p style="margin:8px auto 0;max-width:600px;font-size:13px;color:#666;line-height:1.6;">${tp.overall_suggestions}</p>` : ''}
      </div>
      ${budgetHTML}
      ${mapHTML}
      ${daysHTML}
      ${hotelHTML}
      ${weatherHTML}
      ${footerHTML}
    </div>`
}

// ========== 捕获地图截图 ==========
const captureMapScreenshot = async (): Promise<string> => {
  try {
    const mapEl = document.getElementById('amap-container')
    if (!mapEl || mapEl.clientHeight === 0) {
      console.warn('⚠️ 地图容器不可见或未初始化，跳过地图截图')
      return ''
    }

    // 临时将地图容器显示出来以便截图（可能被 v-show 隐藏）
    const parentCard = document.querySelector('.right-map') as HTMLElement | null
    const wasHidden = parentCard && parentCard.style.display === 'none'
    if (parentCard && wasHidden) {
      parentCard.style.display = 'block'
      parentCard.style.position = 'absolute'
      parentCard.style.left = '-9999px'
    }

    // 等待一帧让渲染生效
    await new Promise(resolve => setTimeout(resolve, 300))

    const mapCanvas = await html2canvas(mapEl, {
      backgroundColor: '#1a1a2e',
      scale: 2,
      logging: false,
      useCORS: true,
      allowTaint: true,
      ignoreElements: (element) => {
        // 忽略地图控制组件（比如 Google 的 +- 缩放按钮、高德控制条）
        // html2canvas 对地图原生 SVG UI 的渲染支持极差，容易出现白底色块
        if (element && element.className && typeof element.className === 'string') {
          if (element.className.includes('gmnoprint') || element.className.includes('amap-controls')) {
            return true
          }
        }
        return false
      }
    })

    // 还原隐藏状态
    if (parentCard && wasHidden) {
      parentCard.style.display = 'none'
      parentCard.style.position = ''
      parentCard.style.left = ''
    }

    return mapCanvas.toDataURL('image/png')
  } catch (err) {
    console.warn('⚠️ 地图截图失败，导出将不包含地图:', err)
    return ''
  }
}

// 导出为图片
const exportAsImage = async () => {
  try {
    message.loading({ content: t('result.messages.generatingImage'), key: 'export', duration: 0 })

    // 1. 先捕获地图截图
    const mapDataUrl = await captureMapScreenshot()

    // 1.5 补齐每天的高德路线摘要（地图未打开过时现算；不改变页面状态）
    await ensureDayRouteLegs()

    // 2. 构建包含地图的完整导出 HTML
    const exportContainer = document.createElement('div')
    exportContainer.innerHTML = buildExportHTML(mapDataUrl)
    exportContainer.style.position = 'absolute'
    exportContainer.style.left = '-9999px'
    document.body.appendChild(exportContainer)

    // 3. 等待二维码等外部图片加载完成
    const images = exportContainer.querySelectorAll('img')
    await Promise.all(
      Array.from(images).map(img =>
        img.complete
          ? Promise.resolve()
          : new Promise(resolve => {
              img.onload = resolve
              img.onerror = resolve
            })
      )
    )

    const canvas = await html2canvas(exportContainer, {
      backgroundColor: '#f0f2f5',
      scale: 2,
      logging: false,
      useCORS: true,
      allowTaint: true
    })

    document.body.removeChild(exportContainer)

    const link = document.createElement('a')
    link.download = `${t('result.export.filePrefix')}_${tripPlan.value?.city}_${new Date().getTime()}.png`
    link.href = canvas.toDataURL('image/png')
    link.click()

    message.success({ content: t('result.messages.imageSuccess'), key: 'export' })
  } catch (error: any) {
    console.error('导出图片失败:', error)
    message.error({ content: t('result.messages.imageFailed', { error: error.message }), key: 'export' })
  }
}
const escapeHtml = (value: unknown): string => {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

const buildMarkerContent = (dayNo: number, stopNo: number): string => {
  return `
    <div class="farway-map-marker">
      <span class="farway-map-marker__core" aria-hidden="true">
        <svg fill="#0F6B4F" width="30px" height="30px" viewBox="0 0 256 256" id="Flat" xmlns="http://www.w3.org/2000/svg">
          <path d="M231.4248,109.2041,169.36426,86.63574,146.7959,24.57422a19.99984,19.99984,0,0,0-37.5918.001L86.63574,86.63574,24.57422,109.2041a19.99984,19.99984,0,0,0,.001,37.5918l62.06054,22.56836,22.56836,62.06152a19.99984,19.99984,0,0,0,37.5918-.001l22.56836-62.06054,62.06152-22.56836a19.99984,19.99984,0,0,0-.001-37.5918Zm-72.01562,38.24219a19.95591,19.95591,0,0,0-11.96289,11.96289l.001-.001L128,212.88672l-19.44629-53.47754A19.95279,19.95279,0,0,0,96.5918,147.44727L43.11328,128l53.47754-19.44629A19.95279,19.95279,0,0,0,108.55273,96.5918L128,43.11328l19.44629,53.47754a19.95279,19.95279,0,0,0,11.96191,11.96191L212.88672,128Z"/>
        </svg>
      </span>
      <span class="farway-map-marker__index" aria-hidden="true">${dayNo}-${stopNo}</span>
    </div>
  `
}

const buildInfoWindowContent = (attraction: any): string => {
  const name = escapeHtml(attraction.name || t('common.noData'))
  const address = escapeHtml(attraction.address || t('common.noData'))
  const visitDuration = Number.isFinite(attraction.visit_duration) ? attraction.visit_duration : '—'
  const dayAttractionText = escapeHtml(
    t('result.mapInfo.dayAttraction', { day: attraction.dayIndex + 1, index: attraction.attrIndex + 1 })
  )
  const minuteUnit = escapeHtml(t('result.minuteUnit'))

  return `
    <div class="farway-map-tooltip farway-map-tooltip--plain">
      <p class="farway-map-tooltip__line farway-map-tooltip__line--title">${name}</p>
      <p class="farway-map-tooltip__line">${dayAttractionText}</p>
      <p class="farway-map-tooltip__line">${address}</p>
      <p class="farway-map-tooltip__line">${visitDuration}${minuteUnit}</p>
    </div>
  `
}

type RouteMode = 'driving' | 'walking' | 'transit' | 'straight'
type RoutePoint = [number, number]

const ROUTE_STYLE_PRESETS: Record<
  RouteMode,
  {
    strokeColor: string
    strokeWeight: number
    strokeOpacity: number
    strokeStyle: 'solid' | 'dashed'
    strokeDasharray?: number[]
    lineJoin?: 'round' | 'miter' | 'bevel'
    lineCap?: 'butt' | 'round' | 'square'
    outlineColor?: string
    borderWeight?: number
  }
> = {
  driving: {
    strokeColor: '#37b4ff',
    strokeWeight: 3.5,
    strokeOpacity: 0.92,
    strokeStyle: 'solid',
    lineJoin: 'round',
    lineCap: 'round',
    outlineColor: 'rgba(4, 19, 32, 0.7)',
    borderWeight: 1,
  },
  walking: {
    strokeColor: '#6ad38f',
    strokeWeight: 3,
    strokeOpacity: 0.9,
    strokeStyle: 'dashed',
    strokeDasharray: [12, 8],
    lineJoin: 'round',
    lineCap: 'round',
    outlineColor: 'rgba(8, 32, 20, 0.5)',
    borderWeight: 0.8,
  },
  transit: {
    strokeColor: '#0F6B4F',
    strokeWeight: 3.2,
    strokeOpacity: 0.9,
    strokeStyle: 'solid',
    lineJoin: 'round',
    lineCap: 'round',
    outlineColor: 'rgba(15, 107, 79, 0.28)',
    borderWeight: 1,
  },
  straight: {
    strokeColor: '#8A938C',
    strokeWeight: 1.5,
    strokeOpacity: 0.7,
    strokeStyle: 'solid',
    strokeDasharray: [10, 10],
    lineJoin: 'round',
    lineCap: 'round',
    outlineColor: 'rgba(27, 36, 32, 0.2)',
    borderWeight: 0.8,
  },
}

type LegMode = 'walking' | 'driving' | 'transit'

const MODE_LABELS: Record<LegMode, string> = {
  walking: '步行',
  driving: '驾车',
  transit: '公交/地铁',
}

const inferLegMode = (transportation: string, distanceM: number): LegMode => {
  const text = transportation || ''
  // 短距离优先步行，避免把 500 米的相邻景点标成公交
  if (distanceM > 0 && distanceM < 700) return 'walking'
  if (/(地铁|公交|轻轨|巴士|公共交通|transit|bus|subway|metro)/i.test(text)) return 'transit'
  if (/(步行|徒步|散步|walk)/i.test(text)) return 'walking'
  if (/(自驾|驾车|开车|打车|出租|drive|car|taxi)/i.test(text)) return 'driving'
  return distanceM > 1600 ? 'driving' : 'walking'
}

const haversineMeters = (start: RoutePoint, end: RoutePoint): number => {
  const radius = 6371000
  const toRad = (value: number) => (value * Math.PI) / 180
  const dLat = toRad(end[1] - start[1])
  const dLng = toRad(end[0] - start[0])
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(start[1])) * Math.cos(toRad(end[1])) * Math.sin(dLng / 2) ** 2
  return 2 * radius * Math.asin(Math.sqrt(a))
}

const formatDurationText = (seconds: number, fallbackMeters: number, mode: LegMode): string => {
  let minutes = seconds > 0
    ? Math.round(seconds / 60)
    : Math.round(fallbackMeters / (mode === 'walking' ? 80 : mode === 'transit' ? 350 : 450))
  minutes = Math.max(1, minutes)
  if (minutes < 60) return `${minutes}分钟`
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return rest > 0 ? `${hours}小时${rest}分` : `${hours}小时`
}

type DayRouteLegSummary = {
  from: string
  to: string
  mode: LegMode
  durationSec: number
  distanceM: number
  order: number
}

// 导出用的每日路线摘要：与地图覆盖物同源，保证「导出图里的路线 == 地图上看到的路线」
const dayRouteLegs = new Map<number, DayRouteLegSummary[]>()
const dayRoutePairs = new Set<string>()

const resetDayRouteLegs = () => {
  dayRouteLegs.clear()
  dayRoutePairs.clear()
}

const recordDayRouteLeg = (dayIndex: number, leg: DayRouteLegSummary) => {
  const key = `${dayIndex}|${leg.from}|${leg.to}`
  if (dayRoutePairs.has(key)) return
  dayRoutePairs.add(key)
  const list = dayRouteLegs.get(dayIndex) || []
  list.push(leg)
  dayRouteLegs.set(dayIndex, list)
}

// 导出时若地图从未打开过（或某天未渲染），按天按顺序现算路线耗时/距离。
// 不创建 Map、不改变页面状态，只复用 AMap 的路径规划服务。
const ensureAmapSdk = async (): Promise<any | null> => {
  let key = getRuntimeMapJsKey()
  if (!key) {
    try {
      key = setRuntimeMapJsKey((await getBackendRuntimeSettings()).vite_amap_web_js_key)
    } catch {
      key = ''
    }
  }
  if (!key) return null
  if (!amapLoaderPromise) {
    amapLoaderPromise = (async () => {
      await ensureAmapSecurityConfig()
      return AMapLoader.load({ key, version: '2.0', plugins: AMAP_PLUGIN_LIST })
    })()
  }
  try {
    return await amapLoaderPromise
  } catch {
    amapLoaderPromise = null
    return null
  }
}

const fetchLegMeta = (
  AMap: any,
  mode: LegMode,
  start: RoutePoint,
  end: RoutePoint,
  city: string
): Promise<{ durationSec: number; distanceM: number } | null> =>
  new Promise((resolve) => {
    let settled = false
    const timer = window.setTimeout(() => finish(null), 8000)
    const finish = (value: { durationSec: number; distanceM: number } | null) => {
      if (settled) return
      settled = true
      window.clearTimeout(timer)
      resolve(value)
    }
    try {
      if (mode === 'transit') {
        if (!AMap?.Transfer) {
          finish(null)
          return
        }
        const transfer = new AMap.Transfer({
          city,
          policy: AMap.TransferPolicy?.LEAST_TIME ?? 0,
          nightflag: 0,
        })
        transfer.search(start, end, (status: string, result: any) => {
          const plan = result?.plans?.[0]
          if (status !== 'complete' || !plan) {
            finish(null)
            return
          }
          finish({ durationSec: Number(plan.time) || 0, distanceM: Number(plan.distance) || 0 })
        })
        return
      }
      const ServiceCtor = mode === 'walking' ? AMap?.Walking : AMap?.Driving
      if (!ServiceCtor) {
        finish(null)
        return
      }
      const service =
        mode === 'driving'
          ? new ServiceCtor({ policy: AMap.DrivingPolicy?.LEAST_TIME ?? 0 })
          : new ServiceCtor({})
      service.search(start, end, (status: string, result: any) => {
        if (status !== 'complete') {
          finish(null)
          return
        }
        const route = result?.routes?.[0]
        finish({ durationSec: Number(route?.time) || 0, distanceM: Number(route?.distance) || 0 })
      })
    } catch {
      finish(null)
    }
  })

const ensureDayRouteLegs = async () => {
  if (!tripPlan.value) return
  const tasks: Array<() => Promise<void>> = []
  const city = tripPlan.value.city || ''

  tripPlan.value.days.forEach((day, dayIndex) => {
    const points = day.attractions.filter(
      (item) =>
        Number.isFinite(Number(item.location?.longitude)) &&
        Number.isFinite(Number(item.location?.latitude))
    )
    for (let i = 0; i < points.length - 1; i += 1) {
      const from = points[i]
      const to = points[i + 1]
      const start: RoutePoint = [Number(from.location!.longitude), Number(from.location!.latitude)]
      const end: RoutePoint = [Number(to.location!.longitude), Number(to.location!.latitude)]
      const mode = inferLegMode(day.transportation || '', haversineMeters(start, end))
      if (dayRoutePairs.has(`${dayIndex}|${from.name}|${to.name}`)) continue

      tasks.push(async () => {
        const AMap = await ensureAmapSdk()
        const meta = AMap ? await fetchLegMeta(AMap, mode, start, end, city) : null
        recordDayRouteLeg(dayIndex, {
          from: from.name,
          to: to.name,
          mode,
          durationSec: meta?.durationSec || 0,
          distanceM: meta?.distanceM || haversineMeters(start, end),
          order: i,
        })
      })
    }
  })

  await runWithConcurrency(tasks, 3)
}

const extractStationName = (text: string): string => {
  const match = String(text || '').match(/([\u4e00-\u9fa5]{2,4}(?:站|机场|航站楼))/)
  return (match?.[1] || '').replace(/^[至到往从在于]/, '')
}

const geocodePlace = (AMap: any, keyword: string, city: string): Promise<RoutePoint | null> =>
  new Promise((resolve) => {
    const cacheKey = `${city}|${keyword}`
    if (geoCache.has(cacheKey)) {
      resolve(geoCache.get(cacheKey) ?? null)
      return
    }
    if (!AMap?.PlaceSearch) {
      resolve(null)
      return
    }
    try {
      const search = new AMap.PlaceSearch({ city, pageSize: 1, pageIndex: 1 })
      search.search(keyword, (_status: string, result: any) => {
        const poi = result?.poiList?.pois?.[0]
        const loc = poi?.location
        const lng = Number(loc?.lng)
        const lat = Number(loc?.lat)
        const point: RoutePoint | null =
          Number.isFinite(lng) && Number.isFinite(lat) ? [lng, lat] : null
        geoCache.set(cacheKey, point)
        resolve(point)
      })
    } catch {
      geoCache.set(cacheKey, null)
      resolve(null)
    }
  })

const toRoutePoint = (raw: any): RoutePoint | null => {
  if (!raw) return null

  if (Array.isArray(raw) && raw.length >= 2) {
    const lng = Number(raw[0])
    const lat = Number(raw[1])
    return Number.isFinite(lng) && Number.isFinite(lat) ? [lng, lat] : null
  }

  if (typeof raw.getLng === 'function' && typeof raw.getLat === 'function') {
    const lng = Number(raw.getLng())
    const lat = Number(raw.getLat())
    return Number.isFinite(lng) && Number.isFinite(lat) ? [lng, lat] : null
  }

  if ('lng' in raw && 'lat' in raw) {
    const lng = Number(raw.lng)
    const lat = Number(raw.lat)
    return Number.isFinite(lng) && Number.isFinite(lat) ? [lng, lat] : null
  }

  if ('longitude' in raw && 'latitude' in raw) {
    const lng = Number(raw.longitude)
    const lat = Number(raw.latitude)
    return Number.isFinite(lng) && Number.isFinite(lat) ? [lng, lat] : null
  }

  return null
}

const parsePolylineString = (polyline: string): RoutePoint[] => {
  if (!polyline) return []

  return polyline
    .split(';')
    .map((pair) => pair.split(','))
    .map((parts) => {
      const lng = Number(parts[0])
      const lat = Number(parts[1])
      return Number.isFinite(lng) && Number.isFinite(lat) ? ([lng, lat] as RoutePoint) : null
    })
    .filter((point): point is RoutePoint => Boolean(point))
}

const dedupeRoutePath = (points: RoutePoint[]): RoutePoint[] => {
  if (points.length <= 1) return points
  return points.filter((point, index, array) => {
    if (index === 0) return true
    const prev = array[index - 1]
    return point[0] !== prev[0] || point[1] !== prev[1]
  })
}

const extractRoutePath = (result: any): RoutePoint[] => {
  const route =
    result?.routes?.[0] ||
    result?.route?.paths?.[0] ||
    result?.route?.routes?.[0] ||
    null

  if (!route) return []

  const steps = route.steps || []
  const points: RoutePoint[] = []

  steps.forEach((step: any) => {
    if (Array.isArray(step?.path)) {
      step.path.forEach((node: any) => {
        const point = toRoutePoint(node)
        if (point) points.push(point)
      })
      return
    }

    if (typeof step?.polyline === 'string') {
      points.push(...parsePolylineString(step.polyline))
    }
  })

  if (points.length > 1) return dedupeRoutePath(points)

  if (typeof route?.polyline === 'string') {
    const fromRoute = dedupeRoutePath(parsePolylineString(route.polyline))
    if (fromRoute.length > 1) return fromRoute
  }

  return []
}

const extractTransferPath = (plan: any): RoutePoint[] => {
  if (!plan) return []

  const direct = Array.isArray(plan.path)
    ? plan.path.map((node: any) => toRoutePoint(node)).filter((point: any): point is RoutePoint => Boolean(point))
    : []
  if (direct.length > 1) return dedupeRoutePath(direct)

  const points: RoutePoint[] = []
  for (const segment of plan.segments ?? []) {
    const stepGroups = [segment?.walking?.steps, segment?.transit?.steps]
    for (const steps of stepGroups) {
      for (const step of steps ?? []) {
        if (Array.isArray(step?.path)) {
          step.path.forEach((node: any) => {
            const point = toRoutePoint(node)
            if (point) points.push(point)
          })
        } else if (typeof step?.polyline === 'string') {
          points.push(...parsePolylineString(step.polyline))
        }
      }
    }
    if (Array.isArray(segment?.transit?.path)) {
      segment.transit.path.forEach((node: any) => {
        const point = toRoutePoint(node)
        if (point) points.push(point)
      })
    }
  }
  return points.length > 1 ? dedupeRoutePath(points) : []
}

const searchRouteDetail = (
  AMap: any,
  mode: LegMode,
  start: RoutePoint,
  end: RoutePoint,
  city: string
): Promise<{ path: RoutePoint[]; durationSec: number; distanceM: number } | null> => {
  const cacheKey = `${mode}|${start[0].toFixed(6)},${start[1].toFixed(6)}|${end[0].toFixed(6)},${end[1].toFixed(6)}`
  const cachedRoute = routeCache.get(cacheKey)
  if (cachedRoute) return Promise.resolve(cachedRoute)
  // 失败的 null 不能永久缓存：高德路径服务可能只是短暂限流/超时，
  // 否则一次失败会让该路段在后续所有刷新中永久消失。
  if (routeCache.has(cacheKey)) routeCache.delete(cacheKey)

  return new Promise((resolve) => {
    let settled = false
    const finish = (value: { path: RoutePoint[]; durationSec: number; distanceM: number } | null) => {
      if (settled) return
      settled = true
      if (value) routeCache.set(cacheKey, value)
      else routeCache.delete(cacheKey)
      resolve(value)
    }
    if (!map) {
      finish(null)
      return
    }
    try {
      if (mode === 'transit') {
        if (!AMap?.Transfer) {
          finish(null)
          return
        }
        const transfer = new AMap.Transfer({
          city,
          policy: AMap.TransferPolicy?.LEAST_TIME ?? 0,
          nightflag: 0,
        })
        transfer.search(start, end, (status: string, result: any) => {
          const plan = result?.plans?.[0]
          if (status !== 'complete' || !plan) {
            finish(null)
            return
          }
          const transferPath = extractTransferPath(plan)
          if (transferPath.length <= 1) {
            finish(null)
            return
          }
          finish({
            path: transferPath,
            durationSec: Number(plan.time) || 0,
            distanceM: Number(plan.distance) || 0,
          })
        })
        return
      }

      const ServiceCtor = mode === 'walking' ? AMap?.Walking : AMap?.Driving
      if (!ServiceCtor) {
        finish(null)
        return
      }
      const service =
        mode === 'driving'
          ? new ServiceCtor({ policy: AMap.DrivingPolicy?.LEAST_TIME ?? 0 })
          : new ServiceCtor({})
      service.search(start, end, (status: string, result: any) => {
        if (status !== 'complete') {
          finish(null)
          return
        }
        const path = extractRoutePath(result)
        const route = result?.routes?.[0]
        finish(
          path.length > 1
            ? {
                path,
                durationSec: Number(route?.time) || 0,
                distanceM: Number(route?.distance) || 0,
              }
            : null
        )
      })
    } catch {
      finish(null)
    }
  })
}

// 初始化地图入口（仅高德地图）
const initMap = async () => {
  const generation = ++mapInitGeneration
  if (generation !== mapInitGeneration) return
  await initAMap(generation)
}

// ===== 3D 地图相机控制 =====
const clearCameraSyncTimer = () => {
  if (cameraSyncTimer !== null) {
    window.clearTimeout(cameraSyncTimer)
    cameraSyncTimer = null
  }
}

const syncCameraState = () => {
  if (!map) return
  try {
    const pitch = Number(map.getPitch?.())
    // 只在「2D/3D 状态」真正翻转时写响应式变量：
    // 拖动旋转时每 100ms 更新 ref 会触发整页 Vue 重渲染，是 3D 手势卡顿的主因之一。
    if (Number.isFinite(pitch)) {
      const nextIs3d = pitch > 10
      const currentIs3d = mapPitch.value > 10
      if (nextIs3d !== currentIs3d) mapPitch.value = pitch
    }
  } catch {
    /* ignore */
  }
}

// 用户手势拖动时最多 10fps 同步状态；程序化相机动画期间不逐帧写响应式变量。
const scheduleCameraStateSync = () => {
  if (cameraAnimating || cameraSyncTimer !== null) return
  cameraSyncTimer = window.setTimeout(() => {
    cameraSyncTimer = null
    syncCameraState()
  }, 100)
}

// 3D/2D 切换使用 AMap 的立即模式：一次写相机，不启动内部动画，
// 避免 3D 建筑块 + 大量路线叠加时动画帧堆积造成“点了没反应/卡死”。
const animateMapCamera = async (targetPitch: number, targetRotation: number) => {
  if (!map || typeof map.setPitch !== 'function' || typeof map.setRotation !== 'function') {
    return
  }
  cameraAnimating = true
  clearCameraSyncTimer()
  try {
    map.setPitch(targetPitch, true)
    const currentRotation = Number(map.getRotation?.() ?? 0) || 0
    if (Math.abs(targetRotation - currentRotation) > 0.5) {
      map.setRotation(targetRotation, true)
    }
  } catch (error) {
    console.warn('地图视角切换失败:', error)
  } finally {
    cameraAnimating = false
    mapPitch.value = targetPitch
    mapRotation.value = ((targetRotation % 360) + 360) % 360
    if (map) syncCameraState()
  }
}

const toggleMapDimension = async () => {
  if (!map || cameraAnimating || mapLoading.value) return
  const currentPitch = Number(map.getPitch?.() ?? mapPitch.value) || 0
  const currentRotation = Number(map.getRotation?.() ?? mapRotation.value) || 0
  const nextPitch = currentPitch > 10 ? 0 : 45
  await animateMapCamera(nextPitch, currentRotation)
}

const resetMapView = async () => {
  if (!map || cameraAnimating) return
  cameraAnimating = true
  try {
    if (amapMarkers.length > 0 && typeof map.setFitView === 'function') {
      map.setFitView(amapMarkers, true, [56, 56, 56, 56], 16)
    }
  } catch {
    /* ignore */
  } finally {
    cameraAnimating = false
  }
  await animateMapCamera(45, 0)
}

// ===== 缩放 / 旋转 / 正北（AMap 2.0 相机立即模式） =====
const zoomMap = (delta: number) => {
  if (!map) return
  try {
    const current = Number(map.getZoom?.() ?? 12) || 12
    map.setZoom(Math.max(3, Math.min(20, current + delta)), true)
  } catch (error) {
    console.warn('地图缩放失败:', error)
  }
}

const rotateMap = (delta: number) => {
  if (!map) return
  try {
    const current = Number(map.getRotation?.() ?? 0) || 0
    const next = ((current + delta) % 360 + 360) % 360
    map.setRotation(next, true)
    mapRotation.value = next
  } catch (error) {
    console.warn('地图旋转失败:', error)
  }
}

const resetMapNorth = () => {
  if (!map) return
  try {
    map.setRotation(0, true)
    mapRotation.value = 0
  } catch (error) {
    console.warn('地图正北复位失败:', error)
  }
}

const setupWebglContextRecovery = () => {
  const canvas = document.querySelector('#amap-container canvas') as HTMLCanvasElement | null
  if (!canvas) return
  canvas.addEventListener(
    'webglcontextlost',
    (event) => {
      event.preventDefault()
      mapUnhealthy = true
      mapLoading.value = false
      message.warning('地图渲染中断，请点击“刷新地图”恢复')
    },
    { once: true }
  )
}

// 空闲预加载：仅加载 SDK 脚本与插件，不创建 Map（容器此时可能还是隐藏的）。
const primeAmapSdk = async () => {
  if (amapLoaderPromise || map) return
  const key = getRuntimeMapJsKey()
  if (!key) return
  const loader = (async () => {
    await ensureAmapSecurityConfig()
    return AMapLoader.load({
      key,
      version: '2.0',
      plugins: AMAP_PLUGIN_LIST,
    })
  })()
  amapLoaderPromise = loader
  loader.catch(() => {
    if (amapLoaderPromise === loader) amapLoaderPromise = null
  })
}

// 初始化高德 3D 地图
const initAMap = async (generation: number) => {
  mapLoading.value = true
  try {
    mapProviderType.value = 'amap'
    let mapJsKey = getRuntimeMapJsKey()
    if (!mapJsKey) {
      // 直达结果页/新浏览器时 localStorage 可能还没有地图 Key，回源后端配置一次。
      try {
        const backend = await getBackendRuntimeSettings()
        mapJsKey = setRuntimeMapJsKey(backend.vite_amap_web_js_key)
      } catch (settingsError) {
        console.warn('读取高德地图 JS Key 失败:', settingsError)
      }
    }
    if (!mapJsKey) {
      mapLoading.value = false
      message.warning('请先在设置中配置高德地图 JS Key')
      return
    }
    if (!amapLoaderPromise) {
      amapLoaderPromise = (async () => {
        await ensureAmapSecurityConfig()
        return AMapLoader.load({
          key: mapJsKey, // 高德地图Web端(JS API) Key
          version: '2.0',
          plugins: AMAP_PLUGIN_LIST,
        })
      })()
    }
    let AMap: any
    try {
      AMap = await amapLoaderPromise
    } catch (error) {
      amapLoaderPromise = null
      throw error
    }

    if (generation !== mapInitGeneration) return

    const isMobile = typeof window !== 'undefined' && window.innerWidth < 768
    const nav = typeof navigator !== 'undefined' ? navigator as Navigator & {
      deviceMemory?: number
    } : null
    const lowPower = Boolean(
      isMobile ||
      (nav?.hardwareConcurrency ?? 8) <= 4 ||
      (nav?.deviceMemory ?? 8) <= 4
    )
    const initialPitch = lowPower ? 30 : 50

    // 防御：容器里已有实例时先销毁，避免同一容器挂多个 WebGL 上下文
    if (map) {
      try {
        map.clearMap()
        map.destroy()
      } catch {
        /* ignore */
      }
      map = null
    }

    // 创建 3D 地图实例：支持俯仰/旋转与建筑块
    map = new AMap.Map('amap-container', {
      zoom: isMobile ? 11 : 12,
      center: [116.397128, 39.916527], // 默认中心点(北京)
      viewMode: '3D',
      pitch: initialPitch,
      rotation: 0,
      rotateEnable: true,
      pitchEnable: true,
      // 低端设备关闭建筑块，保留 3D 俯仰/旋转，避免 GPU 填充率成为瓶颈
      showBuildingBlock: !lowPower,
      features: lowPower ? ['bg', 'road', 'point'] : ['bg', 'road', 'building', 'point'],
      skyColor: '#F6F5F0',
      mapStyle: 'amap://styles/whitesmoke',
      // 开启 preserveDrawingBuffer 才能让 html2canvas 在 WebGL 下截屏成功！
      WebGLParams: {
        preserveDrawingBuffer: true,
      },
    })
    if (generation !== mapInitGeneration) {
      try { map.destroy() } catch { /* ignore */ }
      map = null
      return
    }
    mapPitch.value = initialPitch
    mapRotation.value = 0
    amapInstance = AMap

    // 3D 控件（旋转/俯仰/缩放）
    try {
      const controlBar = new AMap.ControlBar({
        position: { right: '16px', top: '16px' },
        showZoomBar: true,
        showControlButton: true,
      })
      map.addControl(controlBar)
      const scale = new AMap.Scale({ position: { left: '16px', bottom: '16px' } })
      map.addControl(scale)
    } catch (controlError) {
      console.warn('3D 控件加载失败（不影响地图）:', controlError)
    }

    amapGeocoder = new AMap.Geocoder({ city: tripPlan.value?.city || '' })
    map.on('click', handleMapClick)
    setupWebglContextRecovery()
    mapUnhealthy = false

    const finishMapLoading = () => {
      if (generation === mapInitGeneration) {
        mapLoading.value = false
        mapUnhealthy = false
      }
    }
    if (typeof map.on === 'function') {
      map.on('complete', finishMapLoading)
      // 瓦片异常时避免 loading 遮罩一直停留
      window.setTimeout(finishMapLoading, 6000)
    }

    if (typeof map.on === 'function') {
      map.on('rotatechange', () => {
        if (cameraAnimating) return
        scheduleCameraStateSync()
      })
      map.on('pitchchange', () => {
        if (cameraAnimating) return
        scheduleCameraStateSync()
      })
    }

    // 绘制标记与分段路线
    await renderMapAttractions(AMap)

    if (generation !== mapInitGeneration) return
    message.success(t('result.messages.mapLoaded'))
  } catch (error) {
    console.error('地图加载失败:', error)
    mapUnhealthy = true
    mapLoading.value = false
    message.error(t('result.messages.mapLoadFailed'))
  }
}

// 添加景点标记
const clearAmapRendered = () => {
  // 先关掉所有信息窗，再移除覆盖物，避免弹窗 DOM/事件在多次渲染后累积。
  amapInfoWindows.forEach((infoWindow) => {
    try {
      infoWindow.close()
    } catch {
      /* ignore */
    }
  })
  amapInfoWindows = []
  if (map) {
    try {
      map.remove([...amapMarkers, ...amapRouteOverlays, ...amapRouteLabels])
    } catch {
      /* ignore */
    }
  }
  amapMarkers = []
  amapRouteOverlays = []
  amapRouteLabels = []
}

const drawRouteLeg = (
  AMap: any,
  detail: { path: RoutePoint[]; durationSec: number; distanceM: number } | null,
  start: RoutePoint,
  end: RoutePoint,
  mode: LegMode,
  labelPrefix = '',
  labelOffsetX = 0,
  labelOffsetY = 0,
  labelRatio = 0.5
) => {
  if (!map) return null
  const distance = detail?.distanceM || haversineMeters(start, end)
  // 无真实路径时不画整段直线；仅允许 ≤300m 的步行接驳短连接
  if (!detail && distance > 300) {
    console.warn('路线暂不可用，已跳过直线降级:', start, end)
    return null
  }
  const path = detail?.path?.length ? detail.path : [start, end]
  const style = ROUTE_STYLE_PRESETS[detail ? mode : 'straight']
  const polyline = new AMap.Polyline({ path, ...style, showDir: true, zIndex: 90 })
  amapRouteOverlays.push(polyline)
  map.add(polyline)

  const durationText = formatDurationText(detail?.durationSec || 0, distance, mode)
  const midpoint = path[Math.floor(path.length * labelRatio)] || [
    (start[0] + end[0]) / 2,
    (start[1] + end[1]) / 2,
  ]
  const labelText = `${labelPrefix}${MODE_LABELS[mode]} · 约${durationText}`
  if (labelPrefix.includes('接驳')) {
    // 接驳段信息用独立浮层展示，避免与景点标签重叠
    transferSummary.value = labelText
    return polyline
  }
  const label = new AMap.Text({
    text: labelText,
    position: midpoint,
    anchor: 'center',
    offset: new AMap.Pixel(labelOffsetX, labelOffsetY),
    zIndex: 170,
    style: {
      'background-color': 'rgba(255, 255, 255, 0.94)',
      border: '1px solid #E2DFD5',
      'border-radius': '999px',
      padding: '2px 7px',
      color: '#0F6B4F',
      'font-size': '11px',
      'font-weight': '600',
      'box-shadow': '0 2px 6px rgba(27, 36, 32, 0.16)',
      'white-space': 'nowrap',
    },
  })
  amapRouteLabels.push(label)
  map.add(label)
  return polyline
}

const buildArrivalTransferLeg = async (
  AMap: any,
  dayIndex: number
): Promise<{ start: RoutePoint; end: RoutePoint; mode: LegMode; station: string } | null> => {
  if (!tripPlan.value) return null
  const day = tripPlan.value.days?.[dayIndex]
  const hotelLocation = day?.hotel?.location
  if (!day?.is_transfer_day || !hotelLocation) return null

  const hotelLng = Number(hotelLocation.longitude)
  const hotelLat = Number(hotelLocation.latitude)
  if (!Number.isFinite(hotelLng) || !Number.isFinite(hotelLat)) return null

  const allInfoText = tripPlan.value.days.map((item) => item.transfer_info || '').join(' ')
  const stationName =
    extractStationName(day.transfer_info || '') ||
    extractStationName(allInfoText) ||
    `${tripPlan.value.city}站`
  console.debug('[map3d] station', stationName)
  const stationPoint = await geocodePlace(AMap, stationName, tripPlan.value.city)
  console.debug('[map3d] stationPoint', stationPoint)
  if (!stationPoint) return null

  const infoText = `${day.transfer_info || ''} ${allInfoText}`
  const mode: LegMode = /地铁|公交|轻轨|巴士/.test(infoText)
    ? 'transit'
    : /步行/.test(infoText)
      ? 'walking'
      : 'driving'

  return { start: stationPoint, end: [hotelLng, hotelLat], mode, station: stationName }
}

const runWithConcurrency = async (tasks: Array<() => Promise<void>>, limit = 2) => {
  let nextIndex = 0
  const worker = async () => {
    while (true) {
      const index = nextIndex
      nextIndex += 1
      if (index >= tasks.length) return
      try {
        await tasks[index]()
      } catch (error) {
        console.warn('绘制地图路线失败:', error)
      }
    }
  }
  const workers = Array.from(
    { length: Math.min(Math.max(1, limit), Math.max(1, tasks.length)) },
    () => worker()
  )
  await Promise.all(workers)
}

const markersWithinCurrentView = (): boolean => {
  if (!map || amapMarkers.length === 0) return true
  try {
    const bounds = map.getBounds?.()
    if (!bounds) return false
    return amapMarkers.every((marker) => {
      const position = marker.getPosition?.()
      return Boolean(position) && bounds.contains(position)
    })
  } catch {
    return false
  }
}

type MapRenderOptions = {
  /** 数据刷新时保持当前中心/缩放，避免用户正在看的位置被重置。 */
  preserveCamera?: boolean
  /** false = 永不自动适配；默认只在标记不在视野内时适配。 */
  fitView?: boolean
}

const renderMapAttractions = async (AMap: any, options: MapRenderOptions = {}) => {
  if (!tripPlan.value || !map) return
  const token = ++amapRenderToken
  mapLoading.value = true
  transferSummary.value = ''
  clearAmapRendered()

  const dayIndexes: number[] =
    selectedMapDay.value === 'all'
      ? tripPlan.value.days.map((_, index) => index)
      : [selectedMapDay.value as number]

  const arrivalDayIndex = (() => {
    const days = tripPlan.value.days || []
    const byText = days.findIndex(
      (item) => item.is_transfer_day && /(抵达|到达|前往)/.test(item.transfer_info || '')
    )
    return byText >= 0 ? byText : days.findIndex((item) => item.is_transfer_day)
  })()

  const routeTasks: Array<() => Promise<void>> = []

  for (const dayIndex of dayIndexes) {
    const day = tripPlan.value.days?.[dayIndex]
    if (!day) continue

    const attractions = day.attractions
      .filter((attraction) => {
        const lng = Number(attraction.location?.longitude)
        const lat = Number(attraction.location?.latitude)
        return Number.isFinite(lng) && Number.isFinite(lat)
      })
      .map((attraction, attrIndex) => ({ ...attraction, dayIndex, attrIndex }))

    attractions.forEach((attraction, index) => {
      const attractionLng = Number(attraction.location.longitude)
      const attractionLat = Number(attraction.location.latitude)
      const marker = new AMap.Marker({
        position: [attractionLng, attractionLat],
        content: buildMarkerContent(attraction.dayIndex + 1, attraction.attrIndex + 1),
        anchor: 'center',
        offset: new AMap.Pixel(0, 0),
        // 跨天叠加时保持稳定层级，避免同一天/不同天 marker 互相盖住造成“乱跳”。
        zIndex: 120 + dayIndex * 100 + index,
      })
      // 信息窗改为首次交互时再创建：初始化只建 marker，减少一次加载里的
      // DOM/事件对象创建量（10+ 个景点时可见）。
      let infoWindow: any = null
      const openInfoWindow = () => {
        if (!map) return
        if (!infoWindow) {
          infoWindow = new AMap.InfoWindow({
            isCustom: true,
            content: buildInfoWindowContent(attraction),
            offset: new AMap.Pixel(0, -18),
            closeWhenClickMap: true,
          })
          amapInfoWindows.push(infoWindow)
        }
        infoWindow.open(map, marker.getPosition())
      }
      marker.on('mouseover', openInfoWindow)
      marker.on('mouseout', () => { infoWindow?.close() })
      marker.on('click', openInfoWindow)
      amapMarkers.push(marker)
    })

    // 当日酒店标记
    const hotel = day.hotel
    const hotelLng = Number(hotel?.location?.longitude)
    const hotelLat = Number(hotel?.location?.latitude)
    if (hotel && Number.isFinite(hotelLng) && Number.isFinite(hotelLat)) {
      const hotelMarker = new AMap.Marker({
        position: [hotelLng, hotelLat],
        content: '<div class="farway-hotel-marker">宿</div>',
        anchor: 'center',
        zIndex: 160 + dayIndex * 100,
      })
      let hotelInfo: any = null
      const openHotelInfo = () => {
        if (!map) return
        if (!hotelInfo) {
          hotelInfo = new AMap.InfoWindow({
            isCustom: true,
            content: `<div class="farway-map-hotel-info"><strong>${escapeHtml(hotel.name || '')}</strong><p>${escapeHtml(hotel.address || '')}</p></div>`,
            offset: new AMap.Pixel(0, -20),
            closeWhenClickMap: true,
          })
          amapInfoWindows.push(hotelInfo)
        }
        hotelInfo.open(map, hotelMarker.getPosition())
      }
      hotelMarker.on('mouseover', openHotelInfo)
      hotelMarker.on('mouseout', () => { hotelInfo?.close() })
      hotelMarker.on('click', openHotelInfo)
      amapMarkers.push(hotelMarker)
    }

    for (let i = 0; i < attractions.length - 1; i += 1) {
      const startPoint: RoutePoint = [
        Number(attractions[i].location.longitude),
        Number(attractions[i].location.latitude),
      ]
      const endPoint: RoutePoint = [
        Number(attractions[i + 1].location.longitude),
        Number(attractions[i + 1].location.latitude),
      ]
      const mode = inferLegMode(day.transportation || '', haversineMeters(startPoint, endPoint))
      routeTasks.push(async () => {
        const detail = await searchRouteDetail(
          AMap,
          mode,
          startPoint,
          endPoint,
          tripPlan.value?.city || ''
        )
        if (token !== amapRenderToken) return
        // 记录当日路线摘要，供导出图片使用（与地图覆盖物同一份数据）
        recordDayRouteLeg(dayIndex, {
          from: attractions[i].name,
          to: attractions[i + 1].name,
          mode,
          durationSec: detail?.durationSec || 0,
          distanceM: detail?.distanceM || haversineMeters(startPoint, endPoint),
          order: i,
        })
        drawRouteLeg(
          AMap,
          detail,
          startPoint,
          endPoint,
          mode,
          '',
          i % 2 === 0 ? -34 : 34,
          (i % 3 - 1) * 20,
          0.5
        )
      })
    }

    if (dayIndex === arrivalDayIndex) {
      const transferDayIndex = dayIndex
      routeTasks.push(async () => {
        const transferLeg = await buildArrivalTransferLeg(AMap, transferDayIndex)
        if (!transferLeg || token !== amapRenderToken) return
        const detail = await searchRouteDetail(
          AMap,
          transferLeg.mode,
          transferLeg.start,
          transferLeg.end,
          tripPlan.value?.city || ''
        )
        if (token !== amapRenderToken) return
        drawRouteLeg(
          AMap,
          detail,
          transferLeg.start,
          transferLeg.end,
          transferLeg.mode,
          `接驳 · ${transferLeg.station} `,
          0,
          0.72
        )
      })
    }
  }

  // 先把 marker 显示出来，路线在后台逐段补齐，避免地图空白等待。
  try {
    if (amapMarkers.length) {
      map.add(amapMarkers)
      // 默认只在标记超出当前视野时移动相机。切换日期或地点刷新时，
      // 若当前视野已经覆盖目标 marker，就保持中心/缩放不变，避免整张地图“跳一下”。
      const shouldFit = !options.preserveCamera && options.fitView !== false
      if (shouldFit && !markersWithinCurrentView()) {
        map.setFitView(amapMarkers, true, [60, 60, 60, 60], 16)
      }
    }
  } catch (error) {
    console.warn('添加地图景点标记失败:', error)
  } finally {
    mapLoading.value = false
  }

  if (token !== amapRenderToken) return
  await runWithConcurrency(routeTasks, 2)
}

const selectMapDay = async (day: number | 'all') => {
  selectedMapDay.value = day
  if (activeSection.value !== 'map' || !map || !amapInstance) return
  mapLoading.value = true
  try {
    await renderMapAttractions(amapInstance)
  } finally {
    if (mapLoading.value) mapLoading.value = false
  }
}
</script>

<style scoped>

/* ===== Landing 同款视觉基底 - 结果页 ===== */

.result-container {
  min-height: 100vh;
  background: linear-gradient(180deg, #F7F5EF 0%, #EFF5F0 55%, #F7F5EF 100%);
  color: #1B2420;
  position: relative;
  isolation: isolate;
  overflow-x: hidden;
}

.lower-shade {
  position: fixed;
  inset: 0% 0 -1px 0;
  z-index: 0;
  pointer-events: none;
  background: transparent;
  display: none;
}

.lower-shade::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: -28px;
  height: 28px;
  background: linear-gradient(to bottom, rgba(6, 14, 20, 0), transparent);
}

.result-main {
  position: relative;
  z-index: 2;
  padding: 70px 20px 44px;
}

.content-wrapper {
  max-width: 1400px;
  margin: 0 auto;
  display: block;
  border: 1.2px solid #E2DFD5;
  border-radius: 22px;
  background: #FFFFFF;
  box-shadow: 0 24px 80px rgba(27, 36, 32, 0.10);
  padding: 20px;
}

.top-switch-nav {
  display: flex;
  align-items: center;
  gap: 12px;
  justify-content: space-between;
  margin-bottom: 16px;
}

.top-switch-menu-wrap {
  flex: 1;
  min-width: 0;
  overflow-x: hidden;
  overflow-y: hidden;
}

.top-switch-menu {
  width: 100%;
  min-width: 0;
  border-bottom: 1px solid #EFEDE6 !important;
  background: transparent !important;
}

.top-switch-menu :deep(.ant-menu-item) {
  color: #5C675F !important;
  border-radius: 10px 10px 0 0;
  margin-right: 4px !important;
  transition: all 0.2s ease;
}

.top-switch-menu :deep(.ant-menu-item:hover) {
  color: #1B2420 !important;
}

.top-switch-menu :deep(.ant-menu-item-selected) {
  color: #0F6B4F !important;
}

.top-switch-menu :deep(.ant-menu-item-selected::after),
.top-switch-menu :deep(.ant-menu-item-active::after),
.top-switch-menu :deep(.ant-menu-item:hover::after) {
  border-bottom-color: #0F6B4F !important;
}

.top-switch-menu :deep(.ant-menu-overflow) {
  flex-wrap: nowrap;
}

.top-switch-actions {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
}

.top-switch-actions :deep(.ant-btn-default) {
  border: 1.2px solid #DDD9CD !important;
  background: #FFFFFF !important;
  color: #1B2420 !important;
  border-radius: 999px !important;
  height: 34px !important;
  padding: 0 12px !important;
  font-size: 12px !important;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.top-switch-actions :deep(.ant-btn-primary) {
  border: 1.2px solid rgba(15, 107, 79, 0.5) !important;
  background: rgba(15, 107, 79, 0.24) !important;
  color: #0F6B4F !important;
  border-radius: 999px !important;
  height: 34px !important;
  padding: 0 12px !important;
  font-size: 12px !important;
  font-weight: 600;
  letter-spacing: 0.04em;
  box-shadow: none !important;
}

.empty-state-panel {
  max-width: 900px;
  margin: 0 auto;
  border: 1.2px solid #E2DFD5;
  border-radius: 22px;
  background: #FFFFFF;
  box-shadow: 0 24px 80px rgba(27, 36, 32, 0.10);
  padding: 44px 20px;
  text-align: center;
}

.empty-desc {
  color: #5C675F;
}

.empty-back-btn {
  border: 1.2px solid rgba(15, 107, 79, 0.5) !important;
  background: rgba(15, 107, 79, 0.24) !important;
  color: #0F6B4F !important;
  border-radius: 999px !important;
  min-height: 34px !important;
  padding: 0 14px !important;
  font-size: 12px !important;
  font-weight: 600;
  letter-spacing: 0.04em;
  box-shadow: none !important;
}

/* 景点图片样式 */
.attraction-image-wrapper {
  position: relative;
  margin-bottom: 12px;
  border-radius: 12px;
  overflow: hidden;
}

.attraction-image {
  width: 100%;
  height: 200px;
  object-fit: cover;
  transition: transform 0.4s ease;
}

.attraction-image-wrapper:hover .attraction-image {
  transform: scale(1.08);
}

.attraction-badge {
  position: absolute;
  top: 12px;
  left: 12px;
  background: linear-gradient(135deg, #0F6B4F 0%, #0A4F3A 100%);
  color: white;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  box-shadow: 0 4px 12px rgba(15, 107, 79, 0.3);
}

.badge-number {
  font-size: 18px;
}

.price-tag {
  position: absolute;
  top: 12px;
  right: 12px;
  background: rgba(15, 107, 79, 0.9);
  color: white;
  padding: 4px 10px;
  border-radius: 12px;
  font-weight: bold;
  font-size: 14px;
  line-height: 1.2;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 1px;
  box-shadow: 0 4px 12px rgba(15, 107, 79, 0.3);
  backdrop-filter: blur(10px);
}

.price-tag-ref {
  font-size: 9px;
  font-weight: 500;
  opacity: 0.86;
  letter-spacing: 0.02em;
}

.meal-price-note {
  margin-left: 8px;
  color: #0F6B4F;
  font-size: 12px;
  white-space: nowrap;
}

/* 预约提醒样式 */
.reservation-alert {
  margin-top: 10px;
  padding: 8px 12px;
  background: linear-gradient(135deg, rgba(255, 152, 0, 0.12) 0%, rgba(255, 87, 34, 0.08) 100%);
  border: 1px solid rgba(255, 152, 0, 0.35);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.reservation-badge {
  font-size: 13px;
  font-weight: 700;
  color: #ff9800;
}

.reservation-tips {
  font-size: 12px;
  color: #5C675F;
  line-height: 1.5;
}

/* 天气看板样式 */
.weather-section-card {
  /* margin-top: 14px; */
  overflow: hidden;
}

.weather-dashboard {
  display: flex;
  height: 350px;
  /* border-radius: 24px; */
  overflow: hidden;
  /* border: 1px solid #E2DFD5; */
  background: none;
}

.weather-side {
  position: relative;
  flex: 0 0 300px;
  /* min-height: 360px; */
  /* border-radius: 26px; */
  overflow: hidden;
  box-shadow: 0 0 20px -8px rgba(27, 36, 32, 0.10);
  transition: transform 300ms ease;
  transform: translateZ(0) scale(1.02) perspective(1200px);
}

.weather-side:hover {
  transform: scale(1.06) perspective(1400px) rotateY(6deg);
}

.weather-gradient {
  position: absolute;
  inset: 0;
  background-image: linear-gradient(140deg, #72edf2 0%, #5151e5 100%);
  opacity: 0.84;
}

.date-container {
  position: absolute;
  top: 38px;
  left: 38px;
  right: 28px;
  z-index: 2;
}

.date-dayname {
  margin: 0;
  font-size: 26px;
  line-height: 1.12;
  font-weight: 700;
  color: #121A16;
}

.date-day {
  display: block;
  margin-top: 4px;
  font-size: 13px;
  letter-spacing: 0.03em;
  color: rgba(240, 247, 255, 0.84);
}

.location {
  display: inline-flex;
  align-items: center;
  margin-top: 8px;
  font-size: 16px;
  font-weight: bold;
  color: rgba(242, 248, 255, 0.9);
}

.location-icon {
  margin-right: 6px;
}

.weather-container {
  position: absolute;
  left: 28px;
  right: 28px;
  bottom: 28px;
  z-index: 2;
}

.weather-hero-icon {
  display: inline-block;
  color: #f7fbff;
  font-size: 0.78em;
  line-height: 1;
  margin-bottom: -22px;
  margin-left: -20px;
  filter: drop-shadow(0 8px 14px rgba(0, 0, 0, 0.18));
}

.weather-icon {
  position: relative;
  display: inline-block;
  width: 12em;
  height: 10em;
  animation: weather-float 5.5s ease-in-out infinite;
}

.weather-icon .cloud {
  position: absolute;
  z-index: 1;
  top: 50%;
  left: 50%;
  width: 3.6875em;
  height: 3.6875em;
  margin: -1.84375em;
  background: currentColor;
  border-radius: 50%;
  box-shadow:
    -2.1875em 0.6875em 0 -0.6875em,
    2.0625em 0.9375em 0 -0.9375em,
    0 0 0 0.375em #fff,
    -2.1875em 0.6875em 0 -0.3125em #fff,
    2.0625em 0.9375em 0 -0.5625em #fff;
}

.weather-icon .cloud:after {
  content: '';
  position: absolute;
  bottom: 0;
  left: -0.5em;
  display: block;
  width: 4.5625em;
  height: 1em;
  background: currentColor;
  box-shadow: 0 0.4375em 0 -0.0625em #fff;
}

.weather-icon .cloud:nth-child(2) {
  z-index: 0;
  background: #fff;
  box-shadow:
    -2.1875em 0.6875em 0 -0.6875em #fff,
    2.0625em 0.9375em 0 -0.9375em #fff,
    0 0 0 0.375em #fff,
    -2.1875em 0.6875em 0 -0.3125em #fff,
    2.0625em 0.9375em 0 -0.5625em #fff;
  opacity: 0.3;
  transform: scale(0.5) translate(6em, -3em);
  animation: weather-cloud 4s linear infinite;
}

.weather-icon .cloud:nth-child(2):after {
  background: #fff;
}

.weather-icon .sun {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 2.5em;
  height: 2.5em;
  margin: -1.25em;
  background: currentColor;
  border-radius: 50%;
  box-shadow: 0 0 0 0.375em #fff;
  animation: weather-spin 12s infinite linear;
}

.weather-icon .rays {
  position: absolute;
  top: -2em;
  left: 50%;
  display: block;
  width: 0.375em;
  height: 1.125em;
  margin-left: -0.1875em;
  background: #fff;
  border-radius: 0.25em;
  box-shadow: 0 5.375em #fff;
}

.weather-icon .rays:before,
.weather-icon .rays:after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  display: block;
  width: 0.375em;
  height: 1.125em;
  transform: rotate(60deg);
  transform-origin: 50% 3.25em;
  background: #fff;
  border-radius: 0.25em;
  box-shadow: 0 5.375em #fff;
}

.weather-icon .rays:before {
  transform: rotate(120deg);
}

.weather-icon .cloud + .sun {
  margin: -2em 1em;
}

.weather-icon .rain,
.weather-icon .lightning,
.weather-icon .snow {
  position: absolute;
  z-index: 2;
  top: 50%;
  left: 50%;
  width: 3.75em;
  height: 3.75em;
  margin: 0.375em 0 0 -2em;
  background: transparent;
}

.weather-icon .rain:after {
  content: '';
  position: absolute;
  z-index: 2;
  top: 50%;
  left: 50%;
  width: 1.125em;
  height: 1.125em;
  margin: -1em 0 0 -0.25em;
  background: #0cf;
  border-radius: 100% 0 60% 50% / 60% 0 100% 50%;
  box-shadow:
    0.625em 0.875em 0 -0.125em #DDD9CD,
    -0.875em 1.125em 0 -0.125em #DDD9CD,
    -1.375em -0.125em 0 #DDD9CD;
  transform: rotate(-28deg);
  animation: weather-rain 3s linear infinite;
}

.weather-icon .bolt {
  position: absolute;
  top: 50%;
  left: 50%;
  margin: -0.25em 0 0 -0.125em;
  color: #fff;
  opacity: 0.3;
  animation: weather-lightning 2s linear infinite;
}

.weather-icon .bolt:nth-child(2) {
  width: 0.5em;
  height: 0.25em;
  margin: -1.75em 0 0 -1.875em;
  transform: translate(2.5em, 2.25em);
  opacity: 0.2;
  animation: weather-lightning 1.5s linear infinite;
}

.weather-icon .bolt:before,
.weather-icon .bolt:after {
  content: '';
  position: absolute;
  z-index: 2;
  top: 50%;
  left: 50%;
  margin: -1.625em 0 0 -1.0125em;
  border-top: 1.25em solid transparent;
  border-right: 0.75em solid;
  border-bottom: 0.75em solid;
  border-left: 0.5em solid transparent;
  transform: skewX(-10deg);
}

.weather-icon .bolt:after {
  margin: -0.25em 0 0 -0.25em;
  border-top: 0.75em solid;
  border-right: 0.5em solid transparent;
  border-bottom: 1.25em solid transparent;
  border-left: 0.75em solid;
  transform: skewX(-10deg);
}

.weather-icon .bolt:nth-child(2):before {
  margin: -0.75em 0 0 -0.5em;
  border-top: 0.625em solid transparent;
  border-right: 0.375em solid;
  border-bottom: 0.375em solid;
  border-left: 0.25em solid transparent;
}

.weather-icon .bolt:nth-child(2):after {
  margin: -0.125em 0 0 -0.125em;
  border-top: 0.375em solid;
  border-right: 0.25em solid transparent;
  border-bottom: 0.625em solid transparent;
  border-left: 0.375em solid;
}

.weather-icon .flake:before,
.weather-icon .flake:after {
  content: '\2744';
  position: absolute;
  top: 50%;
  left: 50%;
  margin: -1.025em 0 0 -1.0125em;
  color: #fff;
  line-height: 1em;
  opacity: 0.2;
  animation: weather-spin 8s linear infinite reverse;
}

.weather-icon .flake:after {
  margin: 0.125em 0 0 -1em;
  font-size: 1.5em;
  opacity: 0.4;
  animation: weather-spin 14s linear infinite;
}

.weather-icon .flake:nth-child(2):before {
  margin: -0.5em 0 0 0.25em;
  font-size: 1.25em;
  opacity: 0.2;
  animation: weather-spin 10s linear infinite;
}

.weather-icon .flake:nth-child(2):after {
  margin: 0.375em 0 0 0.125em;
  font-size: 2em;
  opacity: 0.4;
  animation: weather-spin 16s linear infinite reverse;
}

.weather-temp {
  margin: 8px 0 0;
  font-size: 56px;
  line-height: 0.95;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.02em;
}

.weather-desc {
  margin: 8px 0 0;
  font-size: 20px;
  color: rgba(245, 249, 255, 0.94);
  font-weight: 600;
}

.weather-info-side {
  flex: 1;
  min-width: 0;
  padding: 16px 30px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.today-info-container {
  /* border-radius: 14px; */
  /* border: 1px solid #EFEDE6;
  background: #F7F5EF; */
}

.today-info {
  padding: 10px 12px;
}

.today-info-item {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  line-height: 1.3;
}

.today-info-item + .today-info-item {
  margin-top: 6px;
  padding-top: 6px;
  /* border-top: 1px solid #F1EFE8; */
}

.today-info-item .wea-title {
  color: #5C675F;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  font-size: 17px;
  font-weight: 600;
  padding: 3px 0;
}

.today-info-item .value {
  color: #1B2420;
  text-align: right;
  font-size: 16px;
}

.week-container {
  margin-top: 0;
  padding-top: 0;
}

.week-container--top {
  margin-bottom: 2px;
}

.week-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.week-list > li {
  width: 86px;
  padding: 8px 8px;
  border-radius: 12px;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease, color 0.2s ease;
  border: 1px solid #EFEDE6;
  background: #F6F4EE;
  color: #5C675F;
}

.week-list > li:hover {
  transform: translateY(-3px);
  background: #E6E3D9;
  color: #1B2420;
  box-shadow: 0 10px 28px rgba(9, 15, 22, 0.32);
}

.week-list > li.active {
  background: #0F6B4F;
  color: #FFFFFF;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.22);
}

.week-list > li .day-icon {
  display: block;
  margin: 0 auto;
}

.week-list > li .day-icon.weather-icon--small {
  width: 12em;
  height: 10em;
  font-size: 0.3em;
  color: inherit;
  animation-duration: 6.2s;
}

.week-list > li .day-name {
  display: block;
  margin-top: 6px;
  text-align: center;
  font-size: 12px;
  letter-spacing: 0.03em;
}

.week-list > li .day-temp {
  display: block;
  text-align: center;
  margin-top: 3px;
  font-weight: 700;
  font-size: 12px;
}

@keyframes weather-spin {
  100% {
    transform: rotate(360deg);
  }
}

@keyframes weather-float {
  0%,
  100% {
    transform: translateY(0);
  }

  50% {
    transform: translateY(-2px);
  }
}

@keyframes weather-cloud {
  0% {
    opacity: 0;
  }

  50% {
    opacity: 0.3;
  }

  100% {
    opacity: 0;
    transform: scale(0.5) translate(-200%, -3em);
  }
}

@keyframes weather-rain {
  0% {
    background: #0cf;
    box-shadow:
      0.625em 0.875em 0 -0.125em #DDD9CD,
      -0.875em 1.125em 0 -0.125em #DDD9CD,
      -1.375em -0.125em 0 #0cf;
  }

  25% {
    box-shadow:
      0.625em 0.875em 0 -0.125em #DDD9CD,
      -0.875em 1.125em 0 -0.125em #0cf,
      -1.375em -0.125em 0 #DDD9CD;
  }

  50% {
    background: #A6ADA6;
    box-shadow:
      0.625em 0.875em 0 -0.125em #0cf,
      -0.875em 1.125em 0 -0.125em #DDD9CD,
      -1.375em -0.125em 0 #DDD9CD;
  }

  100% {
    box-shadow:
      0.625em 0.875em 0 -0.125em #DDD9CD,
      -0.875em 1.125em 0 -0.125em #DDD9CD,
      -1.375em -0.125em 0 #0cf;
  }
}

@keyframes weather-lightning {
  45% {
    color: #fff;
    background: #fff;
    opacity: 0.2;
  }

  50% {
    color: #0cf;
    background: #0cf;
    opacity: 1;
  }

  55% {
    color: #fff;
    background: #fff;
    opacity: 0.2;
  }
}

/* 回到顶部按钮 */
.back-top-button {
  width: 50px;
  height: 50px;
  background: linear-gradient(135deg, #0F6B4F 0%, #0A4F3A 100%);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.03em;
  box-shadow: 0 4px 20px rgba(15, 107, 79, 0.38);
  cursor: pointer;
  transition: all 0.3s ease;
}

.back-top-button:hover {
  transform: scale(1.15);
  box-shadow: 0 6px 28px rgba(15, 107, 79, 0.48);
}

/* 酒店卡片样式 */
.hotel-card {
  background: rgba(15, 107, 79, 0.1) !important;
  border: 1px solid rgba(15, 107, 79, 0.26) !important;
}

.hotel-card :deep(.ant-card-head) {
  background: linear-gradient(135deg, rgba(15, 107, 79, 0.9) 0%, rgba(161, 70, 37, 0.9) 100%) !important;
}

.hotel-title {
  color: white !important;
  font-weight: 600;
}

.hotel-card :deep(.ant-descriptions-item-label) {
  color: #6B7570 !important;
}

.hotel-card :deep(.ant-descriptions-item-content) {
  color: #3A4640 !important;
}

/* 顶部信息区布局 */
.top-info-section {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  align-items: flex-start;
}

.left-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.right-map {
  flex: 1;
}

/* 行程概览卡片 */
.overview-card {
  margin-bottom: 20px;
}

.section-shellless {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

.section-shellless:hover {
  box-shadow: none !important;
  border-color: transparent !important;
}

:deep(.section-shellless > .ant-card-head) {
  display: none !important;
}

:deep(.section-shellless > .ant-card-body) {
  padding: 0 !important;
  background: transparent;
  border-radius: 14px;
}

.overview-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 18px;
}

.overview-meta-item {
  display: inline-flex;
  align-items: center;
  padding: 3px 12px;
  /* border-radius: 999px;
  border: 1px solid #E6E3D9;
  background: #F6F4EE; */
  color: #3A4640;
  font-size: 12px;
  line-height: 1.5;
}

.overview-discover-entry {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin: 0 0 18px;
  padding: 16px 18px;
  border: 1px solid #DCE8DF;
  border-radius: 14px;
  background: linear-gradient(135deg, #F3F8F4 0%, #FAF8F2 100%);
}

.overview-discover-copy {
  min-width: 0;
}

.overview-discover-title {
  margin: 0 0 4px;
  color: #0F6B4F;
  font-size: 15px;
  font-weight: 700;
}

.overview-discover-desc {
  margin: 0;
  color: #5C675F;
  font-size: 12px;
  line-height: 1.6;
}

.overview-discover-btn {
  flex: 0 0 auto;
}

/* ===== 热门景点发现页 ===== */
.discover-page {
  margin-bottom: 20px;
}

.discover-head {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 14px;
}

.discover-back {
  flex: 0 0 auto;
  margin-top: 2px;
  padding: 6px 12px;
  border: 1px solid #DCE8DF;
  border-radius: 10px;
  background: #FFFFFF;
  color: #0F6B4F;
  font-size: 12px;
  cursor: pointer;
}

.discover-heading {
  flex: 1;
  min-width: 0;
}

.discover-heading h2 {
  margin: 0;
  color: #1B2420;
  font-size: clamp(22px, 2vw, 30px);
  font-weight: 400;
  line-height: 1.2;
}

.discover-heading p {
  margin: 5px 0 0;
  color: #6B756E;
  font-size: 12px;
  line-height: 1.5;
}

.discover-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  color: #5C675F;
  font-size: 12px;
}

.discover-day-select {
  min-width: 190px;
}

.discover-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.discover-card {
  overflow: hidden;
  border: 1px solid #E6E3D9;
  border-radius: 14px;
  background: #FFFFFF;
  box-shadow: 0 6px 18px rgba(27, 36, 32, 0.06);
}

.discover-card-media {
  position: relative;
  aspect-ratio: 16 / 10;
  overflow: hidden;
  background: #EEF3EF;
}

.discover-card-media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.discover-rating,
.discover-category {
  position: absolute;
  top: 9px;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: #0F6B4F;
  font-size: 10px;
  font-weight: 700;
  line-height: 1.4;
}

.discover-rating {
  left: 9px;
}

.discover-category {
  right: 9px;
  color: #5C675F;
}

.discover-card-body {
  padding: 13px 14px 14px;
}

.discover-card-body h3 {
  margin: 0 0 6px;
  color: #1B2420;
  font-size: 16px;
  font-weight: 700;
  line-height: 1.3;
}

.discover-card-desc,
.discover-card-address {
  margin: 0 0 6px;
  color: #5C675F;
  font-size: 12px;
  line-height: 1.55;
}

.discover-card-desc {
  display: -webkit-box;
  overflow: hidden;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.discover-card-address {
  color: #7A847D;
}

.discover-card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 10px;
}

.discover-state {
  padding: 36px 16px;
  text-align: center;
  color: #6B756E;
  font-size: 13px;
}

.discover-detail-overlay {
  position: fixed;
  inset: 0;
  z-index: 2400;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 40px 18px;
  overflow-y: auto;
  background: rgba(20, 30, 25, 0.45);
  backdrop-filter: blur(4px);
}

.discover-detail-panel {
  width: min(980px, 100%);
  padding: 18px;
  border-radius: 18px;
  background: #F7F5EF;
  box-shadow: 0 24px 70px rgba(10, 24, 16, 0.28);
}

.discover-detail-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 14px;
  padding: 12px 4px 2px;
  border-top: 1px solid #E2DFD5;
  color: #5C675F;
  font-size: 12px;
}

.phase-lock-overlay {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(20, 30, 25, 0.42);
  backdrop-filter: blur(3px);
  cursor: wait;
}

.phase-lock-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 18px 22px;
  border-radius: 14px;
  background: #FFFFFF;
  color: #1B2420;
  font-size: 14px;
  box-shadow: 0 18px 50px rgba(10, 24, 16, 0.24);
}

.phase-lock-card p {
  margin: 0;
}

.phase-lock-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid #DCE8DF;
  border-top-color: #0F6B4F;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.overview-reminders {
  margin: 0 0 18px;
}

.day-reminders {
  margin: 12px 0 16px;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 22px;
  align-items: stretch;
  padding: 6px 2px 12px;
}

@media (max-width: 1100px) {
  .overview-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 18px;
  }
}

@media (max-width: 600px) {
  .overview-grid {
    grid-template-columns: minmax(0, 1fr);
    gap: 14px;
    padding: 4px 0 8px;
  }
}


/* 预算卡片 */
.budget-card {
  height: fit-content;
}

.budget-detail-panel {
  min-height: 100%;
  border-radius: 14px;
  border: 1px solid #E2DFD5;
  background: #FFFFFF;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.budget-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid #E6E3D9;
}

.budget-toolbar-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.budget-toolbar-label {
  font-size: 12px;
  color: #5C675F;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.budget-select {
  width: 180px;
}

.budget-select :deep(.ant-select-selector) {
  border-radius: 10px !important;
  border-color: #D5D2C6 !important;
  background: #FFFFFF !important;
  color: #1B2420 !important;
}

.budget-select :deep(.ant-select-arrow) {
  color: #5C675F !important;
}

.budget-result-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  padding: 2px 2px 10px;
  border-bottom: 1px solid #E6E3D9;
  color: #5C675F;
  font-size: 12px;
}

.budget-result-day {
  padding: 2px 8px;
  border-radius: 999px;
  background: #E6F1EC;
  color: #0F6B4F;
  font-weight: 650;
}

.budget-result-count {
  color: #8A938C;
}

.budget-result-total {
  margin-left: auto;
  color: #0F6B4F;
  font-weight: 750;
  font-variant-numeric: tabular-nums;
}

.budget-reset-order {
  padding: 0 !important;
  font-size: 12px !important;
}

.budget-detail-list {
  border: 1px solid #E2DFD5;
  border-radius: 12px;
  overflow: hidden;
  background: #FFFFFF;
}

.budget-detail-row {
  display: grid;
  grid-template-columns: minmax(70px, 100px) minmax(58px, 80px) minmax(0, 1fr) minmax(132px, 172px) minmax(110px, 128px);
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  border-bottom: 1px solid #E6E3D9;
  background: #F8F6F0;
  min-width: 0;
}

.budget-detail-row:last-child {
  border-bottom: none;
}

.budget-detail-header {
  background: #F6F4EE;
  font-size: 12px;
  color: #6B7570;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.budget-detail-header > span {
  white-space: nowrap;
}

.budget-detail-header .budget-detail-amount {
  text-align: right;
  justify-self: end;
}

.budget-detail-type,
.budget-detail-day,
.budget-detail-name,
.budget-detail-amount {
  color: #1B2420;
  font-size: 13px;
}

.budget-detail-type,
.budget-detail-day {
  white-space: nowrap;
}

.budget-detail-name {
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.budget-detail-amount {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: #0F6B4F;
  text-align: right;
  justify-self: end;
  white-space: nowrap;
}

.budget-inline-edit {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  justify-content: flex-end;
}

.budget-inline-currency {
  color: #0F6B4F;
  font-weight: 700;
}

.budget-inline-input {
  width: 104px;
}

.budget-inline-input :deep(input) {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.budget-save-btn {
  color: #0F6B4F;
}

.budget-cancel-btn {
  color: #8A938C;
}

.budget-move-btn {
  color: #5C675F;
}

.budget-icon-btn:disabled {
  opacity: 0.25;
  cursor: not-allowed;
}

.budget-detail-action {
  justify-self: end;
}

.budget-action-wrap {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.budget-icon-btn {
  width: 22px;
  height: 22px;
  border: none;
  background: transparent;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.budget-icon-btn svg {
  width: 16px;
  height: 16px;
}

.budget-edit-btn {
  color: #5C675F;
}

.budget-delete-btn {
  color: #5C675F;
}

.budget-edit-btn:hover,
.budget-delete-btn:hover {
  color: #fff;
  transform: scale(1.1);
  /* background: rgba(110, 247, 213, 0.16); */
}

.right-budget-summary {
  flex: 0 0 380px;
  align-self: flex-start;
  min-width: 0;
}

.budget-summary-panel {
  min-height: auto;
  border-radius: 14px;
  border: 1.2px solid #E2DFD5;
  background: #FFFFFF;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.budget-summary-title {
  color: #1B2420;
  font-size: clamp(24px, 2.2vw, 34px);
  font-weight: 300;
  letter-spacing: 0.02em;
  line-height: 1.1;
}

.budget-reference-note {
  margin: 4px 0 2px;
  color: #6B756E;
  font-size: 11px;
  line-height: 1.5;
}

.budget-detail-reference {
  margin: 6px 0 2px;
  color: #6B756E;
  font-size: 11px;
  line-height: 1.5;
}

.budget-summary-total-label {
  margin-top: -8px;
  color: #5C675F;
  font-size: 12px;
  line-height: 1.4;
}

.budget-limit-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid rgba(15, 107, 79, 0.24);
  border-radius: 10px;
  background: rgba(15, 107, 79, 0.06);
  color: #0F6B4F;
  font-size: 12px;
  line-height: 1.4;
}

.budget-limit-bar.over {
  border-color: rgba(190, 72, 55, 0.28);
  background: rgba(190, 72, 55, 0.07);
  color: #A83B2B;
}

.budget-limit-label,
.budget-limit-status {
  white-space: nowrap;
}

.budget-summary-sub-item--intercity .budget-summary-sub-label {
  text-transform: none;
  letter-spacing: 0;
}

.budget-intercity-meta {
  margin-top: 6px;
  color: #5C675F;
  font-size: 12px;
  line-height: 1.5;
}

.budget-exclude-note {
  margin-top: 6px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #F7F5EF;
  color: #6B756E;
  font-size: 12px;
  line-height: 1.5;
}

.budget-summary-total-wrap {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 6px;
  min-width: 0;
}

.budget-summary-currency {
  font-size: clamp(22px, 2.2vw, 42px);
  line-height: 1;
  margin-top: 4px;
  color: #1B2420;
}

.budget-summary-total-value {
  font-size: clamp(40px, 4.4vw, 78px);
  line-height: 1;
  font-weight: 300;
  color: #121A16;
  letter-spacing: 0.01em;
  font-variant-numeric: tabular-nums;
  overflow-wrap: anywhere;
  min-width: 0;
}

.budget-summary-sub-grid {
  margin-top: 2px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 4px 16px;
  min-width: 0;
}

.budget-summary-sub-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  border-top: 1px solid #EFEDE6;
  padding: 10px 0 6px;
}

.budget-summary-sub-item:last-child:nth-child(odd) {
  grid-column: 1 / -1;
}

.budget-summary-sub-value {
  font-size: clamp(20px, 2vw, 32px);
  line-height: 1;
  color: #0F6B4F;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.budget-summary-sub-label {
  font-size: 12px;
  line-height: 1.4;
  letter-spacing: 0.04em;
  color: #5C675F;
  text-transform: uppercase;
}

.budget-pending-wrap {
  margin-top: 4px;
  padding-top: 12px;
  border-top: 1px solid #E6E3D9;
}

.budget-pending-title {
  font-size: 12px;
  letter-spacing: 0.04em;
  color: #5C675F;
  margin-bottom: 8px;
  text-transform: uppercase;
}

.budget-pending-empty {
  font-size: 12px;
  color: #8A938C;
  padding: 8px 0;
}

.budget-pending-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.budget-pending-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 10px;
  background: #F6F4EE;
  border: 1px solid #EFEDE6;
}

.budget-pending-name {
  flex: 1;
  min-width: 0;
  color: #2E3A34;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.budget-restore-btn {
  padding: 0 !important;
}

/* 地图卡片 */
/* 注意：这里必须给 .map-card 一个确定高度。
   之前是 height:100% + min-height:500px，百分比高度无法从 min-height 解析，
   导致 .ant-card-body 高度为 auto、#amap-container 实际高度 0，
   AMap 2.0 在 0 高度容器上 add() overlay 会抛 `Invalid Object: Pixel(NaN, NaN)`，
   表现为"只剩底图、景点标记全部丢失"。 */
.map-card {
  position: relative;
  height: clamp(420px, 62vh, 640px);
  min-height: 420px;
  overflow: hidden;
}

.map-card :deep(.ant-card-body) {
  height: 100%;
  padding: 0;
}

.map-loading-mask {
  position: absolute;
  inset: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: rgba(255, 255, 255, 0.86);
  color: var(--fw-accent, #0f6b4f);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02em;
  pointer-events: none;
}

.map-loading-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(15, 107, 79, 0.18);
  border-top-color: var(--fw-accent, #0f6b4f);
  border-radius: 50%;
  animation: map-loading-spin 0.8s linear infinite;
}

@keyframes map-loading-spin {
  to {
    transform: rotate(360deg);
  }
}

/* 3D 地图悬浮工具条 */
.map-3d-toolbar {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 12;
  display: flex;
  gap: 6px;
  padding: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #E2DFD5;
  box-shadow: 0 6px 18px rgba(27, 36, 32, 0.12);
  backdrop-filter: blur(8px);
}

.map-3d-btn {
  min-width: 46px;
  text-align: center;
  border: none;
  background: transparent;
  color: #3A4640;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  padding: 5px 11px;
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease;
  white-space: nowrap;
}

.map-3d-btn:hover {
  background: #F1EFE8;
  color: #1B2420;
}

.map-3d-btn.active {
  background: #0F6B4F;
  color: #FFFFFF;
}

.map-3d-btn:disabled {
  opacity: 0.55;
  cursor: wait;
}
/* 按天筛选 */
.map-day-filter {
  position: absolute;
  left: 50%;
  bottom: 12px;
  transform: translateX(-50%);
  z-index: 12;
  display: flex;
  gap: 4px;
  max-width: calc(100% - 24px);
  overflow-x: auto;
  padding: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid #E2DFD5;
  box-shadow: 0 6px 18px rgba(27, 36, 32, 0.12);
  backdrop-filter: blur(8px);
  scrollbar-width: none;
}

.map-day-filter::-webkit-scrollbar {
  display: none;
}

.map-day-chip {
  border: none;
  background: transparent;
  color: #3A4640;
  font-size: 12px;
  font-weight: 600;
  padding: 5px 11px;
  border-radius: 999px;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.2s ease, color 0.2s ease;
}

.map-day-chip:hover {
  background: #F1EFE8;
  color: #1B2420;
}

.map-day-chip.active {
  background: #0F6B4F;
  color: #FFFFFF;
}


/* 每日行程卡片 */
.days-card {
  margin-top: 20px;
}

.day-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.day-title {
  font-size: 18px;
  font-weight: 600;
  color: #2E3A34;
}

.day-date {
  font-size: 14px;
  color: #8A938C;
  margin-left: auto;
}

.day-city-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 6px;
  background: rgba(90, 216, 166, 0.15);
  border: 1px solid rgba(90, 216, 166, 0.3);
  color: #5ad8a6;
  font-size: 12px;
  font-weight: 600;
  margin-left: 10px;
}

.day-transfer-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 6px;
  background: rgba(246, 189, 22, 0.15);
  border: 1px solid rgba(246, 189, 22, 0.35);
  color: #f6bd16;
  font-size: 12px;
  font-weight: 600;
  margin-left: 6px;
}

.transfer-info-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  margin-bottom: 14px;
  border-radius: 10px;
  background: rgba(246, 189, 22, 0.08);
  border: 1px solid rgba(246, 189, 22, 0.2);
  font-size: 13px;
  color: #3A4640;
}

.transfer-info-icon {
  font-size: 18px;
}

.transfer-info-label {
  font-weight: 600;
  color: #f6bd16;
}

.day-info {
  margin-bottom: 20px;
  padding: 16px;
  background: #F6F4EE;
  border-radius: 12px;
  border: 1px solid #F3F1EA;
}

.info-row {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
}

.info-row:last-child {
  margin-bottom: 0;
}

.info-row .label {
  font-weight: 600;
  color: #8A938C;
  min-width: 100px;
}

.info-row .value {
  color: #3A4640;
  flex: 1;
}

/* 卡片样式 - 玻璃拟态暗色 */
:deep(.ant-card) {
  border-radius: 16px;
  background: #F6F4EE !important;
  backdrop-filter: blur(20px);
  border: 1px solid #F1EFE8 !important;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  margin-bottom: 20px;
  transition: all 0.3s ease;
  animation: fadeInUp 0.6s ease-out;
  color: #3A4640;
}

:deep(.ant-card:hover) {
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
  border-color: rgba(15, 107, 79, 0.26) !important;
}

:deep(.ant-card-head) {
  background: linear-gradient(135deg, rgba(15, 107, 79, 0.12) 0%, rgba(15, 107, 79, 0.14) 100%) !important;
  color: #0F6B4F !important;
  border-radius: 16px 16px 0 0;
  font-weight: 600;
  border-bottom: 1px solid #F3F1EA !important;
}

:deep(.ant-card-head-title) {
  color: #0F6B4F !important;
  font-size: 18px;
}

:deep(.ant-card-head-title span) {
  color: #0F6B4F !important;
}

:deep(.ant-card-body) {
  color: #3A4640;
}

:deep(.ant-card-body p) {
  color: #5C675F;
}

:deep(.ant-card-body strong) {
  color: #6B7570;
}

/* Collapse 样式 - 暗色 */
:deep(.ant-collapse) {
  border: none;
  background: transparent;
}

:deep(.ant-collapse-item) {
  margin-bottom: 16px;
  border: 1px solid #F1EFE8 !important;
  border-radius: 16px !important;
  overflow: hidden;
  background: #F7F5EF;
}

:deep(.ant-collapse-header) {
  background: #F6F4EE !important;
  padding: 16px 20px !important;
  font-weight: 600;
  color: #3A4640 !important;
}

:deep(.ant-collapse-expand-icon) {
  color: #8A938C !important;
}

:deep(.ant-collapse-content) {
  border-top: 1px solid #F3F1EA !important;
  background: transparent !important;
}

:deep(.ant-collapse-content-box) {
  padding: 20px;
  color: #5C675F;
}

/* Descriptions 暗色 */
:deep(.ant-descriptions) {
  background: transparent;
}

:deep(.ant-descriptions-bordered .ant-descriptions-item-label) {
  background: #F6F4EE !important;
  color: #6B7570 !important;
  border-color: #F3F1EA !important;
}

:deep(.ant-descriptions-bordered .ant-descriptions-item-content) {
  background: transparent !important;
  color: #3A4640 !important;
  border-color: #F3F1EA !important;
}

:deep(.ant-descriptions-item-label) {
  color: #6B7570 !important;
}

:deep(.ant-descriptions-item-content) {
  color: #3A4640 !important;
}

/* Divider 暗色 */
:deep(.ant-divider) {
  border-color: #F1EFE8 !important;
  color: #6B7570 !important;
}

:deep(.ant-divider-inner-text) {
  color: #6B7570 !important;
}

/* Empty 暗色 */
:deep(.ant-empty-description) {
  color: #8A938C !important;
}

/* 景点卡片样式 */
:deep(.ant-list-item) {
  transition: all 0.3s ease;
}

:deep(.ant-list-item:hover) {
  transform: scale(1.02);
}

/* 动画 */
@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .top-info-section {
    flex-direction: column;
  }

  .left-info {
    flex: 1 1 auto;
    width: 100%;
  }

  .right-budget-summary {
    flex: 1 1 auto;
    width: 100%;
  }

  .right-map {
    flex: 0 0 auto;
    width: 100%;
  }

  .budget-summary-panel {
    min-height: auto;
  }

  .budget-detail-list {
    overflow-x: auto;
  }

  .budget-detail-row {
    min-width: 660px;
  }
}

@media (max-width: 768px) {
  .result-main {
    padding: 60px 10px 24px;
  }

  .content-wrapper {
    padding: 14px;
  }

  .top-switch-nav {
    gap: 8px;
  }

  .top-switch-menu-wrap {
    overflow-x: auto;
    overflow-y: hidden;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    -ms-overflow-style: none;
  }

  .top-switch-menu {
    min-width: max-content;
  }

  .top-switch-menu-wrap::-webkit-scrollbar {
    width: 0;
    height: 0;
    display: none;
  }

  .top-switch-actions {
    max-width: 44%;
  }

  .top-switch-actions :deep(.ant-space) {
    column-gap: 6px !important;
    row-gap: 6px !important;
  }

  .top-switch-actions :deep(.ant-btn-default),
  .top-switch-actions :deep(.ant-btn-primary) {
    height: 32px !important;
    padding: 0 10px !important;
    font-size: 11px !important;
  }

  .top-info-section {
    flex-direction: column;
  }

  .left-info {
    flex: auto;
  }

  .weather-dashboard {
    flex-direction: column;
    min-height: auto;
    border-radius: 16px;
  }

  .weather-side {
    flex: 0 0 auto;
    width: 100%;
    min-height: 260px;
    border-radius: 16px 16px 0 0;
    transform: none !important;
  }

  .weather-info-side {
    padding: 12px;
  }

  .weather-temp {
    font-size: 46px;
  }

  .weather-desc {
    font-size: 18px;
  }

  .week-list {
    justify-content: space-between;
  }

  .week-list > li {
    width: calc(33.333% - 7px);
    min-width: 88px;
    padding: 8px 6px;
  }

  .right-budget-summary {
    flex: auto;
    width: 100%;
  }

  .budget-summary-panel {
    min-height: auto;
  }

  .budget-summary-title {
    font-size: 30px;
  }

  .budget-summary-total-value {
    font-size: 56px;
  }

  .budget-summary-sub-value {
    font-size: 24px;
  }

  .overview-meta {
    gap: 8px;
    margin-bottom: 14px;
  }

  .overview-meta-item {
    width: 100%;
    border-radius: 12px;
  }

  .budget-toolbar {
    gap: 8px;
  }

  .budget-detail-panel {
    min-height: auto;
    padding: 14px;
  }

  .budget-toolbar-item {
    width: 100%;
    justify-content: space-between;
  }

  .budget-select {
    width: 170px;
  }

  .budget-detail-list {
    overflow-x: auto;
  }

  .budget-detail-row {
    min-width: 660px;
  }

}

@media (max-width: 640px) {
  .top-switch-nav {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .top-switch-actions {
    max-width: none;
  }

  /* 费用明细：手机端改为卡片式，金额无需横向滚动 */
  .budget-detail-header {
    display: none;
  }

  .budget-detail-list {
    overflow-x: visible;
    border: none;
    background: transparent;
  }

  .budget-detail-row {
    min-width: 0;
    grid-template-columns: auto 1fr auto;
    grid-template-areas:
      "type day amount"
      "name name action";
    gap: 6px 10px;
    padding: 12px;
    margin-bottom: 8px;
    border: 1px solid #E6E3D9;
    border-radius: 12px;
    background: #F7F5EF;
  }

  .budget-detail-row:last-child {
    border-bottom: 1px solid #E6E3D9;
  }

  .budget-detail-type {
    grid-area: type;
    font-size: 12px;
    color: #5C675F;
  }

  .budget-detail-day {
    grid-area: day;
    font-size: 12px;
    color: #6B7570;
  }

  .budget-detail-name {
    grid-area: name;
    white-space: normal;
    overflow: visible;
    text-overflow: clip;
  }

  .budget-detail-amount {
    grid-area: amount;
    justify-self: end;
  }

  .budget-action-wrap {
    grid-area: action;
    justify-self: end;
  }

  .budget-toolbar-item {
    width: 100%;
  }
}


/* 移动端 3D 地图工具条与控件避让 */
@media (max-width: 640px) {
  .map-3d-toolbar {
    top: 8px;
    left: 8px;
    gap: 4px;
    padding: 3px;
  }

  .map-3d-btn {
    font-size: 11px;
    padding: 4px 8px;
  }

  .map-card {
    height: clamp(360px, 58vh, 520px);
    min-height: 360px;
  }
}</style>

<style>
:root {
  --farway-map-accent: #0F6B4F;
  --farway-map-accent-strong: #0A4F3A;
  --farway-map-surface: #FFFFFF;
  --farway-map-border: rgba(15, 107, 79, 0.28);
  --farway-map-text-main: #1B2420;
  --farway-map-text-sub: #5C675F;
}

.farway-map-marker {
  position: relative;
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.farway-map-marker__core {
  position: relative;
  z-index: 1;
  width: 20px;
  height: 20px;
  /* border-radius: 50%; */
  display: inline-flex;
  align-items: center;
  justify-content: center;
  /* background: rgba(0, 0, 0, 0.86);
  border: 1.2px solid rgba(255, 255, 255, 0.82);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.45); */
}

.farway-map-marker__icon {
  width: 12px;
  height: 12px;
  stroke: #ffffff;
  stroke-width: 1.6;
  stroke-linecap: round;
  stroke-linejoin: round;
  fill: none;
}

.farway-map-marker__index {
  position: absolute;
  top: calc(100% - 1px);
  left: 50%;
  transform: translateX(-50%);
  font-size: 11px;
  font-weight: 700;
  line-height: 1.5;
  color: #0F6B4F;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid #E2DFD5;
  border-radius: 999px;
  padding: 0 5px;
  box-shadow: 0 2px 6px rgba(27, 36, 32, 0.12);
  white-space: nowrap;
  pointer-events: none;
}

.farway-map-tooltip {
  max-width: min(320px, calc(100vw - 40px));
  background: transparent;
  border: none;
  box-shadow: none;
  padding: 0;
  color: var(--farway-map-text-main);
  pointer-events: none;
}

.farway-map-tooltip__line {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: #ffd6c7 !important;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.85);
  background-color: rgba(0, 0, 0, 0.05);
  white-space: nowrap;
}

.farway-map-tooltip__line + .farway-map-tooltip__line {
  margin-top: 2px;
}

.farway-map-tooltip__line--title {
  font-size: 15px;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.85);
  font-weight: 700;
  color: #ffffff !important;
}

#amap-container .amap-info-content {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
}

#amap-container .amap-info-sharp {
  display: none !important;
}

/* ===== 地点管理 ===== */
.map-pick-mode {
  cursor: crosshair !important;
}

.farway-hotel-marker {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  background: #1B2420;
  color: #FFFFFF;
  border: 2px solid #FFFFFF;
  box-shadow: 0 4px 12px rgba(27, 36, 32, 0.28);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}

.farway-map-hotel-info {
  min-width: 180px;
  max-width: 260px;
  background: #FFFFFF;
  border: 1px solid #E2DFD5;
  border-radius: 12px;
  padding: 10px 12px;
  box-shadow: 0 8px 24px rgba(27, 36, 32, 0.16);
  color: #1B2420;
}

.farway-map-hotel-info strong {
  font-size: 13px;
}

.farway-map-hotel-info p {
  margin: 4px 0 0;
  font-size: 12px;
  color: #6B7570;
}

.places-drawer__title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #1B2420;
  font-weight: 600;
}

.places-drawer__count {
  min-width: 22px;
  height: 22px;
  padding: 0 7px;
  border-radius: 999px;
  background: #EFF5F0;
  color: #0F6B4F;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.place-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.place-topbar__hint {
  font-size: 11px;
  color: #8A938C;
  line-height: 1.5;
}

.place-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.place-empty {
  padding: 48px 12px;
  text-align: center;
  color: #6B7570;
}

.place-empty__title {
  font-size: 15px;
  color: #1B2420;
  margin-bottom: 6px;
}

.place-empty__desc {
  font-size: 12px;
  line-height: 1.7;
}

.place-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.place-item {
  border: 1px solid #E2DFD5;
  border-radius: 12px;
  padding: 10px 12px;
  background: #FFFFFF;
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.place-item.selected {
  border-color: #0F6B4F;
  box-shadow: 0 0 0 2px rgba(15, 107, 79, 0.12);
}

.place-item__main {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.place-type {
  font-size: 11px;
  line-height: 1.6;
  padding: 1px 8px;
  border-radius: 999px;
  background: #EFF5F0;
  color: #0F6B4F;
}

.place-name {
  font-size: 14px;
  color: #1B2420;
}

.place-day {
  margin-left: auto;
  font-size: 11px;
  color: #8A938C;
}

.place-item__addr {
  margin-top: 5px;
  font-size: 12px;
  color: #6B7570;
  line-height: 1.5;
}

.place-item__price {
  margin-top: 3px;
  font-size: 11px;
  color: #0F6B4F;
  line-height: 1.5;
}

.place-save-status {
  margin: 8px 0 6px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #EFF5F0;
  color: #0F6B4F;
  font-size: 12px;
  line-height: 1.5;
}

.place-item__actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 2px;
}

.place-editor__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  color: #1B2420;
}

.place-search-row {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
}

.place-search-results {
  max-height: 190px;
  overflow-y: auto;
  border: 1px solid #E2DFD5;
  border-radius: 10px;
  margin-bottom: 10px;
}

.place-poi {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 100%;
  padding: 8px 10px;
  border: 0;
  border-bottom: 1px solid #F1EFE8;
  background: #FFFFFF;
  cursor: pointer;
  text-align: left;
}

.place-poi:last-child {
  border-bottom: 0;
}

.place-poi strong {
  font-size: 13px;
  color: #1B2420;
}

.place-poi span {
  font-size: 11px;
  color: #8A938C;
  margin-top: 2px;
}

.place-form {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.place-form label {
  margin-top: 4px;
  font-size: 12px;
  color: #6B7570;
}

.place-coord-row {
  display: flex;
  gap: 8px;
}

.place-pick-btn {
  width: 100%;
}
.farway-route-pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid #E2DFD5;
  background: rgba(255, 255, 255, 0.94);
  color: #0F6B4F;
  font-size: 11px;
  font-weight: 600;
  line-height: 18px;
  white-space: nowrap;
  box-shadow: 0 2px 6px rgba(27, 36, 32, 0.16);
}
.map-transfer-pill {
  position: absolute;
  left: 14px;
  top: 58px;
  z-index: 12;
  max-width: calc(100% - 28px);
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid #E2DFD5;
  background: rgba(255, 255, 255, 0.95);
  color: #0F6B4F;
  font-size: 12px;
  font-weight: 600;
  box-shadow: 0 6px 18px rgba(27, 36, 32, 0.12);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  pointer-events: none;
}</style>
