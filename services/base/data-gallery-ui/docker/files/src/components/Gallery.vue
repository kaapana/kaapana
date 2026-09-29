<template>
  <v-container ref="container" fluid style="height: 100%">
    <v-row>
      <v-col
        v-for="(seriesInstanceUID, index) in seriesInstanceUIDs"
        :key="seriesInstanceUID"
        :cols="cols"
      >
        <v-lazy
          v-if="index !== 0"
          :options="{
            threshold: 0.3,
          }"
          transition="fade-transition"
          class="fill-height"
          :min-height="minHeight"
        >
          <SeriesCard :seriesInstanceUID="seriesInstanceUID" />
        </v-lazy>

        <SeriesCard v-else ref="seriesCard" :seriesInstanceUID="seriesInstanceUID" />
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import SeriesCard from './SeriesCard.vue'
import { debounce } from '@/utils/utils'
import { readSettings } from '@/static/defaultUIConfig'

const props = withDefaults(defineProps<{ seriesInstanceUIDs?: string[] }>(), {
  seriesInstanceUIDs: () => [],
})

const container = ref<any>(null)
const seriesCard = ref<any>(null)
const cols = ref(2)
const minHeight = ref(100)
let ro: ResizeObserver | null = null

function firstCardEl(): HTMLElement | null {
  const inst = Array.isArray(seriesCard.value) ? seriesCard.value[0] : seriesCard.value
  return (inst?.$el as HTMLElement) ?? null
}

function containerEl(): HTMLElement | null {
  return (container.value?.$el as HTMLElement) ?? null
}

// Cards after the first render only when scrolled into view. Until then their
// placeholder is about as tall as the first card, so the grid keeps its height
// and does not jump as cards appear.
const updateMinHeight = debounce(() => {
  const el = firstCardEl()
  if (el) minHeight.value = el.clientHeight * 0.85
}, 50)

function onResize() {
  const _cols = readSettings().datasets.cols
  if (_cols !== 'auto') {
    cols.value = _cols
  } else {
    let containerWidth: number
    const el = containerEl()
    if (!el) {
      containerWidth = window.innerWidth
    } else {
      containerWidth = el.offsetWidth
    }
    if (containerWidth < 500) {
      cols.value = 6
    } else if (containerWidth < 650) {
      cols.value = 4
    } else if (containerWidth < 1080) {
      cols.value = 3
    } else if (containerWidth < 1920) {
      cols.value = 2
    } else {
      cols.value = 1
    }
  }
  updateMinHeight()
}

onMounted(() => {
  ro = new ResizeObserver(debounce(onResize, 100))
  const el = containerEl()
  if (el) ro.observe(el)
  nextTick(() => {
    const cardEl = firstCardEl()
    if (cardEl) minHeight.value = cardEl.clientHeight * 0.85
  })
})

onBeforeUnmount(() => {
  ro?.disconnect()
  ro = null
})
</script>

<style scoped>
.v-col {
  /* 4px step of the spacing scale (guidelines, "Spacing and shape"). */
  padding: 4px;
}
</style>
