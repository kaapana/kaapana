<template>
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

    <v-progress-linear
      v-if="loading"
      indeterminate
      color="primary"
      data-testid="dashboard-progress"
    />

    <v-card-text>
      <div v-if="failure" class="text-center py-8" data-testid="dashboard-failure">
        <div class="text-body-2 text-medium-emphasis mb-2">
          The statistics for the current selection could not be loaded.
        </div>
        <v-btn variant="text" color="primary" @click="updateDashboard">Try again</v-btn>
        <v-btn variant="text" @click="showFailureDetails">Details</v-btn>
      </div>

      <div
        v-else-if="Object.keys(histograms).length === 0"
        class="text-body-2 text-medium-emphasis text-center py-8"
      >
        {{
          loading
            ? 'Loading statistics…'
            : 'No statistics for the current selection. Select series, or widen the search, to see their distribution here.'
        }}
      </div>

      <VueApexCharts
        v-else
        v-for="[key, values] in Object.entries(histograms)"
        :key="JSON.stringify({ [key]: values })"
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
import { apiErrorInfo, type ApiErrorInfo } from '@kaapana/base-ui'
import { loadDashboard } from '@/common/api.service'
import { useFailureDetailsStore } from '@/stores/failureDetails'

const props = withDefaults(
  defineProps<{
    seriesInstanceUIDs?: string[]
    fields?: string[]
    allPatients?: boolean
    searchQuery?: Record<string, unknown>
    seriesLoading?: boolean
  }>(),
  {
    seriesInstanceUIDs: () => [],
    fields: () => [],
    allPatients: false,
    seriesLoading: false,
  },
)

const emit = defineEmits<{ dataPointSelection: [payload: { key: string; value: string }] }>()

const theme = useTheme()
const failureDetails = useFailureDetailsStore()

const METRICS = ['Patients', 'Studies', 'Series'] as const

const histograms = ref<Record<string, any>>({})
const metrics = ref<Record<string, any>>({})
const loading = ref(false)
const failure = ref<ApiErrorInfo | null>(null)

function getApexChartsOptions(key: string, values: any): any {
  const current = theme.global.current.value
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
      mode: current.dark ? 'dark' : 'light',
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
        colors: [current.colors['on-primary']],
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
    colors: [current.colors.primary],
  }
}

// Each call gets a new id. A response is applied only if its id is still the
// newest, so a slow answer for an earlier selection cannot overwrite the
// current one or end its loading state.
let dashboardRequest = 0
function updateDashboard() {
  const request = ++dashboardRequest
  if (props.seriesInstanceUIDs.length === 0 && !props.allPatients) {
    histograms.value = {}
    metrics.value = {}
    failure.value = null
    loading.value = false
    return
  }
  let series = props.seriesInstanceUIDs
  let query: any = []
  if (props.allPatients) {
    series = []
    query = props.searchQuery
  }
  loading.value = true
  failure.value = null
  loadDashboard(series, props.fields, query)
    .then((data) => {
      if (request !== dashboardRequest) return
      histograms.value = data['histograms'] || {}
      metrics.value = data['metrics'] || {}
    })
    .catch((error: unknown) => {
      if (request !== dashboardRequest) return
      // On failure, clear leftovers of the previous selection so they don't
      // read as this one's result.
      histograms.value = {}
      metrics.value = {}
      failure.value = apiErrorInfo(error)
    })
    .finally(() => {
      if (request === dashboardRequest) loading.value = false
    })
}

function showFailureDetails() {
  if (!failure.value) return
  failureDetails.show({
    title: 'Statistics not loaded',
    text: 'The statistics for the current selection could not be loaded.',
    error: failure.value,
  })
}

function dataPointSelection(config: any, key: string, value: any) {
  emit('dataPointSelection', {
    key: key,
    value: Object.keys(value['items'])[config['dataPointIndex']],
  })
}

// Load statistics only once the gallery's series have arrived. Until then the
// selection is still changing, and each change would trigger a load.
watch(
  () => [props.seriesInstanceUIDs, props.allPatients, props.searchQuery, props.seriesLoading],
  () => {
    if (!props.seriesLoading) updateDashboard()
  },
)
onMounted(() => {
  if (!props.seriesLoading) updateDashboard()
})
</script>

<style>
.apexcharts-toolbar {
  z-index: 0 !important;
}

.apexcharts-canvas > svg {
  background-color: transparent !important;
}
</style>
