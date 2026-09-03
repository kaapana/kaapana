<template>
  <!-- Flat: this fills the sidebar pane, which is already a surface. -->
  <v-card :elevation="0" class="rounded-0" style="min-height: 100%">
    <v-card-text>
      <v-row align="center" justify="center" class="text-center">
        <v-col v-for="metric in METRICS" :key="metric">
          <div class="text-overline text-medium-emphasis">{{ metric }}</div>
          <div class="text-h5">{{ metrics[metric] ?? '—' }}</div>
        </v-col>
      </v-row>
    </v-card-text>

    <v-divider />

    <v-card-text>
      <div v-if="loading" class="d-flex flex-column align-center ga-3 py-8">
        <v-progress-circular indeterminate color="primary" />
        <span class="text-body-2 text-medium-emphasis">Loading statistics…</span>
      </div>

      <!-- An empty chart area says why it is empty rather than rendering
           nothing (guidelines, "Empty states"). -->
      <div
        v-else-if="Object.keys(histograms).length === 0"
        class="text-body-2 text-medium-emphasis text-center py-8"
      >
        {{
          failed
            ? 'The statistics for the current selection could not be loaded.'
            : 'No statistics for the current selection. Select series, or widen the search, to see their distribution here.'
        }}
      </div>

      <VueApexCharts
        v-else
        v-for="[key, values] in Object.entries(histograms)"
        :key="JSON.stringify({ key: values })"
        :options="getApexChartsOptions(key, values)"
        :series="[
          {
            name: key,
            data: Object.values(values['items']),
          },
        ]"
        type="bar"
      >
      </VueApexCharts>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useTheme } from 'vuetify'
import VueApexCharts from 'vue3-apexcharts'
import { notify } from '@kyvg/vue3-notification'
import { loadDashboard } from '@/common/api.service'
import { apiErrorText } from '@/utils/errors'

const props = withDefaults(
  defineProps<{
    seriesInstanceUIDs?: string[]
    fields?: string[]
    allPatients?: boolean
    searchQuery?: Record<string, unknown>
  }>(),
  {
    seriesInstanceUIDs: () => [],
    fields: () => [],
    allPatients: false,
  },
)

const emit = defineEmits<{ dataPointSelection: [payload: { key: string; value: string }] }>()

const theme = useTheme()

const METRICS = ['Patients', 'Studies', 'Series'] as const

const histograms = ref<Record<string, any>>({})
const metrics = ref<Record<string, any>>({})
const loading = ref(false)
// Kept apart from "nothing to show": a failed load must not be presented as an
// empty collection (guidelines, "Empty states").
const failed = ref(false)

function getApexChartsOptions(key: string, values: any): any {
  const isDark = theme.global.current.value.dark
  return {
    chart: {
      id: key,
      animations: {
        enabled: false,
      },
      events: {
        dataPointSelection: (_event: any, _chartContext: any, config: any) => {
          return dataPointSelection(config, key, values)
        },
      },
      toolbar: {
        show: true,
        offsetX: 0,
        offsetY: 0,
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
        export: {
          csv: {
            filename: undefined,
            columnDelimiter: ',',
            headerCategory: 'category',
            headerValue: 'value',
            dateFormatter(timestamp: number) {
              return new Date(timestamp).toDateString()
            },
          },
          svg: {
            filename: undefined,
          },
          png: {
            filename: undefined,
          },
        },
        autoSelected: 'zoom',
      },
      zoom: {
        enabled: false,
        type: 'x',
        autoScaleYaxis: true,
      },
    },
    theme: {
      mode: isDark ? 'dark' : 'light',
    },
    title: {
      text: key,
    },
    plotOptions: {
      bar: {
        barHeight: '100%',
        dataLabels: {
          position: 'center',
        },
      },
    },
    dataLabels: {
      enabled: true,
      style: {
        colors: ['#fff'],
      },
    },
    grid: {
      show: true,
      xaxis: {
        lines: {
          show: false,
        },
      },
      yaxis: {
        lines: {
          show: true,
        },
      },
    },
    xaxis: {
      categories: Object.keys(values['items']),
      tickPlacement: 'on',
    },
    colors: [
      isDark
        ? theme.themes.value.kaapanaThemeDark.colors.primary
        : theme.themes.value.kaapanaThemeLight.colors.primary,
    ],
  }
}

function updateDashboard() {
  if (props.seriesInstanceUIDs.length === 0 && !props.allPatients) {
    histograms.value = {}
    metrics.value = {}
    failed.value = false
    return
  }
  let series = props.seriesInstanceUIDs
  let query: any = []
  if (props.allPatients) {
    series = []
    query = props.searchQuery
  }
  loading.value = true
  failed.value = false
  loadDashboard(series, props.fields, query)
    .then((data) => {
      histograms.value = data['histograms'] || {}
      metrics.value = data['metrics'] || {}
    })
    // loadDashboard does not report; keep the charts from the last good load.
    .catch((error: any) => {
      failed.value = true
      notify({
        title: 'Statistics not loaded',
        text: apiErrorText(error, 'The statistics for the current selection could not be loaded.'),
        type: 'error',
      })
    })
    .finally(() => {
      loading.value = false
    })
}

function dataPointSelection(config: any, key: string, value: any) {
  emit('dataPointSelection', {
    key: key,
    value: Object.keys(value['items'])[config['dataPointIndex']],
  })
}

watch(() => props.seriesInstanceUIDs, updateDashboard)
onMounted(updateDashboard)
</script>

<style>
.apexcharts-toolbar {
  z-index: 0 !important;
}

.apexcharts-canvas > svg {
  background-color: transparent !important;
}
</style>
