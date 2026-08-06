<template>
  <v-card elevation="0" style="min-height: 100%">
    <v-card-title>
      <v-container align-items="center">
        <v-row align="center" justify="center">
          <v-col>
            <v-row align="center" justify="center"> Patients </v-row>
            <v-row align="center" justify="center">
              {{ metrics['Patients'] || 'N/A' }}
            </v-row>
          </v-col>
          <v-col>
            <v-row align="center" justify="center"> Studies </v-row>
            <v-row align="center" justify="center">
              {{ metrics['Studies'] || 'N/A' }}
            </v-row>
          </v-col>
          <v-col>
            <v-row align="center" justify="center"> Series </v-row>
            <v-row align="center" justify="center">
              {{ metrics['Series'] || 'N/A' }}
            </v-row>
          </v-col>
        </v-row>
      </v-container>
    </v-card-title>

    <v-card-text>
      <VueApexCharts
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

const histograms = ref<Record<string, any>>({})
const metrics = ref<Record<string, any>>({})

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
  } else {
    let series = props.seriesInstanceUIDs
    let query: any = []
    if (props.allPatients) {
      series = []
      query = props.searchQuery
    }
    loadDashboard(series, props.fields, query)
      .then((data) => {
        histograms.value = data['histograms'] || {}
        metrics.value = data['metrics'] || {}
      })
      // loadDashboard does not report; keep the charts from the last good load.
      .catch((error: any) =>
        notify({ title: 'Error', text: error.response?.data?.detail ?? error.message, type: 'error' }),
      )
  }
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
