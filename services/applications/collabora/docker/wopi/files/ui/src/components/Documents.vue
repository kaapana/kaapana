<template>
  <v-container class="documents">
    <div class="d-flex flex-wrap align-center ga-4 mb-4">
      <v-text-field
        v-model="filter"
        class="documents__search"
        label="Search"
        :prepend-inner-icon="kaapanaIcons.search"
        clearable
        hide-details
        single-line
      />
      <v-select
        v-model="sortKey"
        class="documents__sort"
        :items="sortOptions"
        label="Sort by"
        hide-details
      />
      <v-btn
        color="primary"
        :prepend-icon="kaapanaIcons.refresh"
        :loading="rescanning"
        :disabled="loading"
        @click="rescan"
      >
        Check for new documents
      </v-btn>
    </div>

    <v-alert v-if="failure" type="error" variant="tonal" class="mb-4" :text="failure.text">
      <template #append>
        <v-btn variant="text" @click="detailsOpen = true">Details</v-btn>
        <v-btn variant="text" :loading="rescanning" @click="rescan">Try again</v-btn>
      </template>
    </v-alert>

    <div v-if="loading" class="d-flex justify-center pa-8">
      <v-progress-circular indeterminate color="primary" aria-label="Loading documents" />
    </div>

    <template v-else-if="loaded">
      <v-card v-if="visibleDocuments.length">
        <v-list lines="two">
          <v-list-item
            v-for="doc in visibleDocuments"
            :key="`${doc.file.bucket}/${doc.file.path}`"
            :href="doc.url"
            target="_blank"
            rel="noopener"
            :title="doc.file.path"
            :subtitle="`${doc.file.bucket} · Modified ${formatDate(doc.file.modification_time)}`"
            :aria-label="`${doc.file.path}: ${doc.action_name} in ${doc.app_name} (opens in a new tab)`"
          >
            <template #prepend>
              <v-avatar rounded="0">
                <v-img v-if="doc.favicon" :src="doc.favicon" alt="" />
                <v-icon v-else icon="mdi-file-document-outline" />
              </v-avatar>
            </template>
            <template #append>
              <v-icon :icon="kaapanaIcons.externalLink" size="small" />
            </template>
          </v-list-item>
        </v-list>
      </v-card>

      <v-empty-state
        v-else-if="documents.length"
        :icon="kaapanaIcons.search"
        size="56"
        title="No matching documents"
        :text="`No document path contains “${filter}”.`"
      >
        <template #actions>
          <v-btn color="primary" variant="text" @click="filter = ''">Clear search</v-btn>
        </template>
      </v-empty-state>

      <v-empty-state
        v-else
        size="56"
        title="No documents yet"
        text="Office documents stored in MinIO appear here. Check for new documents after uploading one."
      />
    </template>

    <ErrorDetailsDialog
      v-model="detailsOpen"
      title="Documents could not be loaded"
      :text="failure?.text"
      :error="failure?.info"
    />
  </v-container>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  apiErrorInfo,
  apiErrorText,
  ErrorDetailsDialog,
  kaapanaIcons,
  type ApiErrorInfo,
} from '@kaapana/base-ui'
import {
  documentUpdatesUrl,
  fetchDocuments,
  rescanDocuments,
  type DocumentEntry,
} from '@/api/documents'

type SortKey = 'path' | 'modification_time'

const RECONNECT_DELAY_MS = 5000

const sortOptions: { value: SortKey; title: string }[] = [
  { value: 'modification_time', title: 'Last modified' },
  { value: 'path', title: 'Path' },
]

const documents = ref<DocumentEntry[]>([])
const loaded = ref(false)
const loading = ref(false)
const rescanning = ref(false)
const failure = ref<{ text: string; info: ApiErrorInfo } | null>(null)
const detailsOpen = ref(false)
const filter = ref<string | null>('')
const sortKey = ref<SortKey>('modification_time')

const visibleDocuments = computed(() => {
  const needle = (filter.value ?? '').toLowerCase()
  const matching = documents.value.filter((doc) => doc.file.path.toLowerCase().includes(needle))
  return sortKey.value === 'path'
    ? matching.sort((a, b) => a.file.path.localeCompare(b.file.path))
    : matching.sort((a, b) => b.file.modification_time.localeCompare(a.file.modification_time))
})

const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

function formatDate(value: string): string {
  return dateFormat.format(new Date(value))
}

function fail(err: unknown, text: string) {
  failure.value = { text: apiErrorText(err, text), info: apiErrorInfo(err) }
}

let latestLoad = 0

async function load() {
  const request = ++latestLoad
  try {
    const result = await fetchDocuments()
    if (request !== latestLoad) return
    documents.value = result
    loaded.value = true
    failure.value = null
  } catch (err) {
    if (request === latestLoad) fail(err, 'The document list could not be loaded.')
  }
}

async function rescan() {
  rescanning.value = true
  if (!loaded.value) loading.value = true
  try {
    await rescanDocuments()
    await load()
  } catch (err) {
    fail(err, 'Checking MinIO for new documents failed.')
  } finally {
    rescanning.value = false
    loading.value = false
  }
}

let socket: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | undefined
let unmounted = false

function connect() {
  socket = new WebSocket(documentUpdatesUrl())
  socket.onmessage = (event) => {
    try {
      if (JSON.parse(event.data).type === 'update') load()
    } catch {
      console.error('Ignoring malformed document update', event.data)
    }
  }
  socket.onclose = () => {
    if (unmounted) return
    reconnectTimer = setTimeout(() => {
      connect()
      load()
    }, RECONNECT_DELAY_MS)
  }
}

onMounted(() => {
  rescan()
  connect()
})

onBeforeUnmount(() => {
  unmounted = true
  clearTimeout(reconnectTimer)
  socket?.close()
})
</script>

<style scoped>
.documents {
  max-width: 1200px;
}

.documents__search {
  flex: 1 1 240px;
}

.documents__sort {
  flex: 0 1 200px;
}
</style>
