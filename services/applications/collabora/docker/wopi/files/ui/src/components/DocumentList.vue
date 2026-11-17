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
        :loading="refreshing"
        :disabled="loading"
        @click="refresh"
      >
        Refresh
      </v-btn>
    </div>

    <v-alert v-if="failure" type="error" variant="tonal" class="mb-4" :text="failure.text">
      <template #append>
        <v-btn variant="text" @click="detailsOpen = true">Details</v-btn>
        <v-btn variant="text" :loading="refreshing" @click="refresh">Try again</v-btn>
      </template>
    </v-alert>

    <div v-if="loading" class="d-flex justify-center pa-8">
      <v-progress-circular indeterminate color="primary" aria-label="Loading documents" />
    </div>

    <template v-else-if="loaded">
      <v-empty-state
        v-if="!documents.length"
        size="56"
        title="No documents yet"
        text="Office documents in the MinIO bucket of this project appear here."
      />

      <template v-else>
        <nav v-if="!searching" class="documents__crumbs mb-2" aria-label="Folder">
          <template v-for="(crumb, index) in crumbs" :key="index">
            <v-icon v-if="index > 0" :icon="folderIcons.separator" size="small" />
            <span
              v-if="index === crumbs.length - 1"
              class="documents__crumb documents__crumb--current"
              aria-current="location"
            >
              {{ crumb.title }}
            </span>
            <v-btn
              v-else
              variant="text"
              size="small"
              class="documents__crumb"
              @click="folder = crumb.path"
            >
              {{ crumb.title }}
            </v-btn>
          </template>
        </nav>
        <p v-else class="text-body-2 text-medium-emphasis mb-2" role="status">
          {{ rows.length }} {{ rows.length === 1 ? 'document' : 'documents' }} in all folders
        </p>

        <v-card v-if="rows.length">
          <v-table class="documents__table">
            <thead>
              <tr>
                <th>Name</th>
                <th class="d-none d-sm-table-cell">Modified</th>
                <th class="d-none d-sm-table-cell text-end">Size</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="row in rows" :key="rowKey(row)">
                <tr v-if="row.kind === 'folder'" class="documents__row" @click="folder = row.path">
                  <td>
                    <button
                      type="button"
                      class="documents__name"
                      :aria-label="`Open folder ${row.name}`"
                      @click.stop="folder = row.path"
                    >
                      <v-avatar rounded="0" size="24">
                        <v-icon :icon="folderIcons.folder" color="primary" />
                      </v-avatar>
                      <span>{{ row.name }}</span>
                    </button>
                  </td>
                  <td class="d-none d-sm-table-cell">{{ formatDate(row.modified) }}</td>
                  <td class="d-none d-sm-table-cell text-end text-medium-emphasis">
                    {{ row.count }} {{ row.count === 1 ? 'document' : 'documents' }}
                  </td>
                </tr>
                <tr v-else class="documents__row">
                  <td>
                    <a
                      class="documents__name"
                      :href="row.doc.url"
                      target="_blank"
                      rel="noopener"
                      :aria-label="`${row.doc.file.path}: ${row.doc.action_name} in ${row.doc.app_name} (opens in a new tab)`"
                    >
                      <v-avatar rounded="0" size="24">
                        <v-img v-if="row.doc.favicon" :src="row.doc.favicon" alt="" />
                        <v-icon v-else :icon="folderIcons.file" />
                      </v-avatar>
                      <span>{{ row.name }}</span>
                      <v-icon :icon="kaapanaIcons.externalLink" size="x-small" />
                    </a>
                  </td>
                  <td class="d-none d-sm-table-cell">{{ formatDate(row.modified) }}</td>
                  <td class="d-none d-sm-table-cell text-end">{{ formatSize(row.size) }}</td>
                </tr>
              </template>
            </tbody>
          </v-table>
        </v-card>

        <v-empty-state
          v-else
          :icon="kaapanaIcons.search"
          size="56"
          title="No matching documents"
          :text="`No document path contains “${filter}”.`"
        >
          <template #actions>
            <v-btn color="primary" variant="text" @click="filter = ''">Clear search</v-btn>
          </template>
        </v-empty-state>
      </template>
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
import { documentUpdatesUrl, fetchDocuments, type DocumentEntry } from '@/api/documents'
import {
  closestFolder,
  folderRows,
  formatSize,
  searchRows,
  sortRows,
  type Row,
  type SortKey,
} from '@/utils/documentTree'

const folderIcons = {
  folder: 'mdi-folder',
  file: 'mdi-file-document-outline',
  separator: 'mdi-chevron-right',
}

const RECONNECT_DELAY_MS = 5000

const sortOptions: { value: SortKey; title: string }[] = [
  { value: 'name', title: 'Name' },
  { value: 'modified', title: 'Last modified' },
]

const documents = ref<DocumentEntry[]>([])
const loaded = ref(false)
const loading = ref(false)
const refreshing = ref(false)
const failure = ref<{ text: string; info: ApiErrorInfo } | null>(null)
const detailsOpen = ref(false)
const filter = ref<string | null>('')
const sortKey = ref<SortKey>('name')
const folder = ref<string[]>([])

const searching = computed(() => !!filter.value?.trim())

const rows = computed<Row[]>(() =>
  sortRows(
    searching.value
      ? searchRows(documents.value, filter.value!.trim())
      : folderRows(documents.value, folder.value),
    sortKey.value,
  ),
)

const crumbs = computed(() => [
  { title: 'Documents', path: [] as string[] },
  ...folder.value.map((name, i) => ({ title: name, path: folder.value.slice(0, i + 1) })),
])

function rowKey(row: Row): string {
  return row.kind === 'folder'
    ? `folder:${row.path.join('/')}`
    : `file:${row.doc.file.bucket}/${row.doc.file.path}`
}

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
    folder.value = closestFolder(result, folder.value)
    loaded.value = true
    failure.value = null
  } catch (err) {
    if (request === latestLoad) fail(err, 'The document list could not be loaded.')
  }
}

async function refresh() {
  refreshing.value = true
  if (!loaded.value) loading.value = true
  try {
    await load()
  } finally {
    refreshing.value = false
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
  refresh()
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

.documents__crumbs {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

.documents__crumb {
  text-transform: none;
  letter-spacing: normal;
}

.documents__crumb--current {
  padding: 0 8px;
  font-size: 0.875rem;
  font-weight: 500;
}

.documents__row {
  cursor: pointer;
}

.documents__name {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  color: inherit;
  text-decoration: none;
  text-align: start;
  word-break: break-word;
}

.documents__name:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}
</style>
