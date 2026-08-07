<template>
  <v-dialog :model-value="modelValue" max-width="900" @update:model-value="emit('update:modelValue', $event)">
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2">mdi-database-outline</v-icon>
        {{ projectStore.selectedProject.name ?? 'Project' }} in detail
        <v-spacer />
        <v-btn icon variant="text" @click="emit('update:modelValue', false)">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
      <v-card-text>
        <v-progress-circular v-if="loading" indeterminate class="d-block mx-auto my-8" />
        <!-- Ahead of `loaded`, so a failed refetch shows the error rather than
             the numbers it could not refresh. -->
        <div v-else-if="failed" class="text-medium-emphasis text-center my-4">
          Could not load project statistics
        </div>
        <template v-else-if="loaded">
          <v-row dense class="text-center mb-2">
            <v-col v-for="label in ['Patients', 'Studies', 'Series']" :key="label" cols="4">
              <div class="text-h5">{{ metrics[label] ?? 'N/A' }}</div>
              <div class="text-body-2">{{ label }}</div>
            </v-col>
          </v-row>
          <div v-if="!Object.keys(histograms).length" class="text-medium-emphasis text-center my-4">
            No dataset statistics available
          </div>
          <v-row v-else>
            <v-col v-for="[key, values] in Object.entries(histograms)" :key="key" cols="12" md="6">
              <HistogramChart :title="key" :items="values.items" />
            </v-col>
          </v-row>
        </template>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import HistogramChart from '@/components/HistogramChart.vue'
import { useProjectStore } from '@kaapana/base-ui'
import { loadDashboard, type DashboardData } from '@/api/dashboard'
import { settings as defaultSettings } from '@/static/defaultUIConfig'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()

const projectStore = useProjectStore()

const loading = ref(false)
const loaded = ref(false)
const failed = ref(false)
const metrics = ref<DashboardData['metrics']>({})
const histograms = ref<DashboardData['histograms']>({})

// Fetch fresh on every open so the dialog reflects data ingested since mount.
watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    loading.value = true
    failed.value = false
    const settings = localStorage['settings'] ? JSON.parse(localStorage['settings']) : defaultSettings
    try {
      const data = await loadDashboard(settings.landingPage ?? [])
      metrics.value = data.metrics || {}
      histograms.value = data.histograms || {}
      loaded.value = true
    } catch {
      failed.value = true
    } finally {
      loading.value = false
    }
  },
)
</script>
