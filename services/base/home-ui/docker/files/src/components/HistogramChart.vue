<template>
  <VueApexCharts :options="options" :series="series" type="bar" height="240" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useTheme } from 'vuetify'
import VueApexCharts from 'vue3-apexcharts'

const props = defineProps<{
  title: string
  items: Record<string, number>
}>()

const theme = useTheme()

const series = computed(() => [{ name: props.title, data: Object.values(props.items) }])

const options = computed(() => ({
  chart: {
    id: props.title,
    animations: { enabled: false },
    toolbar: {
      show: true,
      // apexcharts 3 never rendered zoom/pan tools on category bar charts;
      // apexcharts 6 does, so switch them off to keep the old look.
      tools: {
        download: true,
        selection: false,
        zoom: false,
        zoomin: false,
        zoomout: false,
        pan: false,
        reset: false,
      },
    },
    zoom: { enabled: false },
  },
  theme: { mode: theme.current.value.dark ? 'dark' : 'light' },
  title: { text: props.title },
  plotOptions: {
    bar: { barHeight: '100%', dataLabels: { position: 'center' } },
  },
  dataLabels: { enabled: true, style: { colors: ['#fff'] } },
  grid: {
    xaxis: { lines: { show: false } },
    yaxis: { lines: { show: true } },
  },
  xaxis: { categories: Object.keys(props.items), tickPlacement: 'on' },
  colors: [theme.current.value.colors.primary],
}))
</script>

<style>
.apexcharts-toolbar {
  z-index: 0 !important;
}

.apexcharts-canvas > svg {
  background-color: transparent !important;
}
</style>
