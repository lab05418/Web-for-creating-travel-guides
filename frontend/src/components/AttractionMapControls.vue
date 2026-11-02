<template>
  <div class="map-3d-toolbar" role="group" :aria-label="label">
    <button type="button" class="map-3d-btn" :class="{ active: is3d }" :title="labels.toggle3d" @click="emit('toggle3d')">
      3D
    </button>

    <span class="map-3d-group" role="group" :aria-label="labels.zoom">
      <button type="button" class="map-3d-btn map-3d-btn--icon" :title="labels.zoomIn" @click="emit('zoom-in')">+</button>
      <button type="button" class="map-3d-btn map-3d-btn--icon" :title="labels.zoomOut" @click="emit('zoom-out')">−</button>
    </span>

    <span class="map-3d-group" role="group" :aria-label="labels.rotate">
      <button type="button" class="map-3d-btn map-3d-btn--icon" :title="labels.rotateLeft" @click="emit('rotate-left')">⟲</button>
      <button type="button" class="map-3d-btn map-3d-btn--icon" :title="labels.rotateRight" @click="emit('rotate-right')">⟳</button>
      <button type="button" class="map-3d-btn map-3d-btn--icon" :title="labels.north" @click="emit('north')">N</button>
    </span>

    <button type="button" class="map-3d-btn" :title="labels.reset" @click="emit('reset')">
      {{ labels.reset }}
    </button>
    <button type="button" class="map-3d-btn" :class="{ active: pickMode }" :title="labels.places" @click="emit('places')">
      {{ labels.places }}
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  is3d: boolean
  pickMode: boolean
  label: string
  labels: {
    toggle3d: string
    zoom: string
    zoomIn: string
    zoomOut: string
    rotate: string
    rotateLeft: string
    rotateRight: string
    north: string
    reset: string
    places: string
  }
}>()

const emit = defineEmits<{
  (e: 'toggle3d'): void
  (e: 'zoom-in'): void
  (e: 'zoom-out'): void
  (e: 'rotate-left'): void
  (e: 'rotate-right'): void
  (e: 'north'): void
  (e: 'reset'): void
  (e: 'places'): void
}>()
</script>

<style scoped>
.map-3d-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}

.map-3d-group {
  display: inline-flex;
  gap: 2px;
  padding: 2px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.72);
}

.map-3d-btn--icon {
  min-width: 26px;
  padding: 3px 6px;
  font-size: 13px;
  line-height: 1.2;
}
</style>
