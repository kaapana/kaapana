<template>
  <div>

      <!-- ===== HEADER ===== -->
      <v-row class="mb-2">
        <v-col cols="12">
          <div class="d-flex align-center justify-space-between mb-4">
            <h1 class="text-h5 mb-0">Loki Logs</h1>
            <v-btn color="primary" :loading="queryLoading" prepend-icon="mdi-magnify" @click="runQuery">
              Run Query
            </v-btn>
          </div>

          <LokiFilterBar
            v-model="filters"
            :namespaces="namespaces"
            :pods="pods"
            :containers="containers"
          />

          <!-- LogQL Preview -->
          <div class="d-flex align-center gap-2 mt-1">
            <v-btn variant="text" size="small" @click="showLogQL = !showLogQL">
              <v-icon size="16" class="mr-1">{{ showLogQL ? 'mdi-eye-off' : 'mdi-eye' }}</v-icon>
              {{ showLogQL ? 'Hide' : 'Show' }} LogQL
            </v-btn>
          </div>
          <v-expand-transition>
            <v-sheet v-if="showLogQL" class="pa-3 mt-1 rounded text-caption font-mono" color="surface-variant">
              {{ currentLogQL || '— set namespace to build query —' }}
            </v-sheet>
          </v-expand-transition>
        </v-col>
      </v-row>

      <!-- ===== RESULTS ===== -->
      <v-row>
        <v-col cols="12">

          <LoadingState v-if="queryLoading" min-height="200px" />

          <ErrorState v-else-if="queryError" :message="queryError" />

          <template v-else-if="streams.length > 0">
            <div class="d-flex justify-space-between align-center mb-2">
              <span class="text-caption text-medium-emphasis">
                {{ totalLines }} log lines across {{ streams.length }} stream(s)
              </span>
              <v-btn variant="text" size="small" prepend-icon="mdi-content-copy" @click="copyLogs">
                Copy
              </v-btn>
            </div>
            <div class="log-output">
              <template v-for="stream in streams" :key="JSON.stringify(stream.stream)">
                <div v-for="[tsNs, line] in stream.values" :key="tsNs" class="log-line">
                  <span class="log-ts">{{ formatTs(tsNs) }}</span>
                  <span class="log-text">{{ line }}</span>
                </div>
              </template>
            </div>
          </template>

          <EmptyState v-else-if="queried && streams.length === 0"
            message="No logs found for the selected filters and time range." />

          <EmptyState v-else type="info">
            Select a <strong>namespace</strong> and click <strong>Run Query</strong>.
          </EmptyState>

        </v-col>
      </v-row>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000" location="top right">
      {{ snackbar.message }}
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import LokiFilterBar from './LokiFilterBar.vue'
import LoadingState from '@/components/logging/shared/LoadingState.vue'
import ErrorState from '@/components/logging/shared/ErrorState.vue'
import EmptyState from '@/components/logging/shared/EmptyState.vue'
import { lokiApi } from '@/api/loki/lokiApi'
import { defaultLokiFilters, buildLogQL, getTimeRange } from '@/types/loki'
import type { LokiStream } from '@/types/loki'

// ── Filters ──────────────────────────────────────────────────────────────────
const filters  = ref(defaultLokiFilters())
const showLogQL = ref(false)

const currentLogQL = computed(() => buildLogQL(filters.value))

// ── Label autocomplete data ───────────────────────────────────────────────────
const namespaces = ref<string[]>([])
const pods       = ref<string[]>([])
const containers = ref<string[]>([])

async function loadNamespaces() {
  try { namespaces.value = await lokiApi.getLabelValues('namespace') }
  catch { namespaces.value = [] }
}

async function loadPods(namespace: string) {
  try {
    pods.value = await lokiApi.getLabelValues('pod',
      namespace ? `{namespace=~"${namespace}"}` : undefined
    )
  } catch { pods.value = [] }
}

async function loadContainers(namespace: string) {
  try {
    containers.value = await lokiApi.getLabelValues('container',
      namespace ? `{namespace=~"${namespace}"}` : undefined
    )
  } catch { containers.value = [] }
}

// Reload pods + containers when namespace changes; clear selections to avoid stale values
watch(() => filters.value.namespace, (ns) => {
  filters.value = { ...filters.value, pod: '.+', container: '.+' }
  loadPods(ns)
  loadContainers(ns)
})

loadNamespaces()

// ── Query ─────────────────────────────────────────────────────────────────────
const streams      = ref<LokiStream[]>([])
const queryLoading = ref(false)
const queryError   = ref<string | null>(null)
const queried      = ref(false)

const totalLines = computed(() =>
  streams.value.reduce((sum, s) => sum + s.values.length, 0)
)

async function runQuery() {
  const query = currentLogQL.value
  if (!query) return

  queryLoading.value = true
  queryError.value   = null
  queried.value      = false

  try {
    const { start, end } = getTimeRange(filters.value)
    streams.value = await lokiApi.queryRange({
      query,
      start,
      end,
      limit:     filters.value.limit,
      direction: filters.value.direction,
    })
  } catch (err: any) {
    queryError.value = err?.response?.data || err?.message || 'Query failed'
    streams.value = []
  } finally {
    queryLoading.value = false
    queried.value = true
  }
}

// ── Formatting ────────────────────────────────────────────────────────────────
function formatTs(tsNs: string): string {
  return new Date(parseInt(tsNs) / 1e6).toISOString().replace('T', ' ').replace('Z', '')
}

// ── Clipboard ─────────────────────────────────────────────────────────────────
const snackbar = ref({ show: false, message: '', color: 'success' })

function copyLogs() {
  const text = streams.value
    .flatMap(s => s.values.map(([ts, line]) => `${formatTs(ts)}  ${line}`))
    .join('\n')
  navigator.clipboard.writeText(text).then(() => {
    snackbar.value = { show: true, message: 'Copied to clipboard', color: 'success' }
  })
}
</script>

<style scoped>
.log-output {
  background-color: #1e1e1e;
  color: #d4d4d4;
  font-family: 'Roboto Mono', monospace;
  font-size: 0.8rem;
  line-height: 1.5;
  border-radius: 4px;
  padding: 12px;
  max-height: 600px;
  overflow-y: auto;
}

.log-line {
  display: flex;
  gap: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}

.log-ts {
  color: #858585;
  flex-shrink: 0;
  user-select: none;
}

.log-text {
  flex: 1;
}

.font-mono {
  font-family: 'Roboto Mono', monospace;
}
</style>
