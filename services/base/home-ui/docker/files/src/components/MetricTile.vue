<template>
  <!-- h-100: a value that wraps to two lines must not leave its row-mate short. -->
  <v-card variant="tonal" class="metric-tile" height="100%">
    <v-card-text class="pb-0">
      <div class="d-flex align-center">
        <v-icon size="small" class="mr-2">{{ icon }}</v-icon>
        <span class="text-body-2">{{ label }}</span>
      </div>
      <div class="text-h4 mt-1">{{ formattedValue }}</div>
    </v-card-text>
    <VueApexCharts :options="sparklineOptions" :series="sparklineSeries" type="area" height="60" />
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useTheme } from 'vuetify'
import VueApexCharts from 'vue3-apexcharts'

const props = defineProps<{
  label: string
  icon: string
  value: number | null
  unit: 'percent' | 'bytesPerSecond'
  history: number[]
}>()

const theme = useTheme()

function formatBytesPerSecond(value: number): string {
  const units = ['B/s', 'KB/s', 'MB/s', 'GB/s']
  let v = value
  let i = 0
  while (v >= 1000 && i < units.length - 1) {
    v /= 1000
    i++
  }
  return `${v >= 100 || i === 0 ? Math.round(v) : v.toFixed(1)} ${units[i]}`
}

const formattedValue = computed(() => {
  if (props.value === null) return '—'
  return props.unit === 'percent'
    ? `${Math.round(props.value)} %`
    : formatBytesPerSecond(props.value)
})

const sparklineSeries = computed(() => [{ name: props.label, data: [...props.history] }])

const sparklineOptions = computed(() => ({
  chart: {
    sparkline: { enabled: true },
    animations: { enabled: false },
  },
  stroke: { curve: 'smooth', width: 2 },
  fill: { type: 'gradient', gradient: { opacityFrom: 0.4, opacityTo: 0.05 } },
  tooltip: { enabled: false },
  colors: [theme.current.value.colors.primary],
}))
</script>

<style scoped>
.metric-tile {
  overflow: hidden;
}
</style>
