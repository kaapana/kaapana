<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { notify } from '@kyvg/vue3-notification'
import { ConfirmDialog, apiErrorInfo, type ApiErrorInfo } from '@kaapana/base-ui'
import { hasVisibleFocus, useFocusReturn } from '@/composables/useFocusReturn'
import { useFailureDetailsStore } from '@/stores/failureDetails'
import { loadDatasets, deleteDataset } from '@/common/api.service'
import type { Dataset } from '@/types'
import { kaapanaIcons } from '@/utils/galleryIcons'
import { sameDataset } from '@/utils/datasets'
import { notifyFailure } from '@/utils/notifyFailure'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ close: [editedDatasets: boolean] }>()

const datasets = ref<any[]>([])
const loading = ref(false)
const loadFailure = ref<ApiErrorInfo | null>(null)
const failureDetails = useFailureDetailsStore()
const deleting = ref(false)
const search = ref<string>('')
const dialogDelete = ref(false)
const sortBy = [{ key: 'name', order: 'asc' as const }]
const headers = [
  { title: 'Name', align: 'start' as const, key: 'name' },
  { title: 'Access', key: 'access_level' },
  { title: 'Size', key: 'size' },
  { title: 'User', key: 'username' },
  { title: 'Created', key: 'time_created' },
  { title: 'Updated', key: 'time_updated' },
  { title: 'Actions', key: 'actions', sortable: false },
]
const editedDatasets = ref(false)
type DatasetRow = Dataset & { size: number }
// editedItem: copy of the row the delete confirmation is about.
// deletingItem: the row whose delete request is running (its button spins).
const editedItem = ref<DatasetRow | null>(null)
const deletingItem = ref<DatasetRow | null>(null)
const searchField = ref<{ focus: () => void } | null>(null)

const deleteText = computed(() => {
  const item = editedItem.value
  if (!item) return ''
  return (
    `The dataset “${item.name}” (${item.access_level}) is deleted for everyone who can see it. ` +
    `The ${item.size ?? 0} series it references stay in the project; only the grouping is deleted. ` +
    'This cannot be undone.'
  )
})

async function loadDatasetsRows() {
  return (await loadDatasets(false)).map((dataset) => ({
    ...dataset,
    size: dataset.identifiers.length,
  }))
}

async function refreshDatasets() {
  loading.value = true
  loadFailure.value = null
  try {
    datasets.value = await loadDatasetsRows()
  } catch (error: unknown) {
    loadFailure.value = apiErrorInfo(error)
  } finally {
    loading.value = false
  }
}

function deleteItem(item: any) {
  if (deleting.value) return
  editedItem.value = { ...item }
  dialogDelete.value = true
}

async function deleteItemConfirm() {
  if (deleting.value || !editedItem.value) return
  const item = editedItem.value
  deleting.value = true
  deletingItem.value = item
  try {
    const successful = await deleteDataset(item.name, item.access_level)
    if (successful) {
      notify({
        title: 'Dataset deleted',
        text: `The dataset “${item.name}” was deleted.`,
        type: 'success',
      })
      datasets.value = datasets.value.filter((d) => !sameDataset(d, item))
      editedDatasets.value = true
    }
  } catch (error: unknown) {
    notifyFailure('Dataset not deleted', `The dataset “${item.name}” could not be deleted.`, error)
  } finally {
    deleting.value = false
    deletingItem.value = null
  }
  await keepFocusInDialog()
}

function showLoadFailureDetails() {
  if (!loadFailure.value) return
  failureDetails.show({
    title: 'Could not load the datasets',
    text: 'The dataset service could not be reached or reported an error.',
    error: loadFailure.value,
  })
}

/** After the confirmation: a deleted row takes its focused button with it,
 *  so move focus back into the dialog. */
async function keepFocusInDialog() {
  await nextTick()
  if (hasVisibleFocus()) return
  searchField.value?.focus()
}

const show = computed({
  get() {
    return props.modelValue
  },
  set() {
    // Closing reports the deletions upward: Refuse to close while a delete runs.
    if (deleting.value) return
    emit('close', editedDatasets.value)
  },
})

watch(
  () => props.modelValue,
  () => {
    refreshDatasets()
  },
)

onMounted(() => {
  refreshDatasets()
})

const { restoreFocus } = useFocusReturn(() => props.modelValue)
onUnmounted(restoreFocus)
</script>

<template>
  <v-dialog v-model="show" max-width="900" :persistent="deleting">
    <v-card :elevation="5">
      <v-card-title class="text-h6">Datasets</v-card-title>
      <v-card-text>
        <v-text-field
          ref="searchField"
          v-model="search"
          :append-inner-icon="kaapanaIcons.search"
          label="Search datasets"
          single-line
          clearable
          hide-details
          density="compact"
          variant="underlined"
          class="mb-4"
        ></v-text-field>
        <v-data-table
          :headers="headers"
          :items="datasets"
          :sort-by="sortBy"
          :search="search"
          :loading="loading"
          loading-text="Loading datasets…"
        >
          <template v-slot:[`item.time_created`]="{ item }">
            {{ new Date(item.time_created).toLocaleString() }}
          </template>
          <template v-slot:[`item.time_updated`]="{ item }">
            {{ new Date(item.time_updated).toLocaleString() }}
          </template>
          <template v-slot:[`item.actions`]="{ item }">
            <v-btn
              :icon="kaapanaIcons.delete"
              :aria-label="`Delete dataset ${item.name} (${item.access_level})`"
              variant="text"
              size="small"
              density="comfortable"
              :loading="sameDataset(deletingItem, item)"
              @click="deleteItem(item)"
            />
          </template>
          <template v-slot:no-data>
            <v-alert
              v-if="loadFailure"
              type="error"
              variant="tonal"
              density="compact"
              class="my-4 text-start"
              title="Could not load the datasets"
              text="The dataset service could not be reached or reported an error."
            >
              <template #append>
                <v-btn variant="text" @click="refreshDatasets">Try again</v-btn>
                <v-btn variant="text" @click="showLoadFailureDetails">Details</v-btn>
              </template>
            </v-alert>
            <div v-else-if="search" class="text-body-2 text-medium-emphasis py-6">
              No dataset matches “{{ search }}”. Clear or change the search text.
            </div>
            <div v-else class="text-body-2 text-medium-emphasis py-6">
              No datasets have been created in this project yet. Select series in the gallery and
              use “Save selection as dataset” to create one.
            </div>
          </template>
        </v-data-table>
      </v-card-text>
      <v-divider></v-divider>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="text" :disabled="deleting" @click="show = false">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <ConfirmDialog
    v-model="dialogDelete"
    title="Delete dataset?"
    :text="deleteText"
    confirm-text="Delete"
    color="error"
    @confirm="deleteItemConfirm"
    @after-leave="keepFocusInDialog"
  />
</template>
