<template>
  <v-dialog
    :model-value="datasets_store.showValidationResults"
    max-width="900"
    scrollable
    @update:model-value="(value: boolean) => !value && onValidationResultClose()"
  >
    <v-card :elevation="5">
      <v-toolbar flat color="transparent">
        <v-toolbar-title class="text-h6">Validation report</v-toolbar-title>
        <v-spacer></v-spacer>
        <v-menu location="bottom end">
          <template v-slot:activator="{ props: activator }">
            <v-btn
              v-bind="activator"
              :icon="galleryIcons.more"
              aria-label="Report actions"
              variant="text"
            />
          </template>
          <v-list>
            <v-list-item
              :prepend-icon="kaapanaIcons.start"
              title="Re-run validation"
              @click="runValidationWorkflow(validationResultItem)"
            />
            <v-list-item
              :prepend-icon="kaapanaIcons.delete"
              title="Delete report"
              @click="deleteValidationResult(validationResultItem)"
            />
            <v-list-item
              :prepend-icon="galleryIcons.downloadFile"
              title="Download report"
              @click="downloadValidationResult(validationResultItem)"
            />
          </v-list>
        </v-menu>
      </v-toolbar>
      <v-divider />
      <v-card-text v-if="validationResultItem != null">
        <div
          v-if="validationResultLookup.loading"
          class="d-flex flex-column align-center ga-3 py-8"
        >
          <v-progress-circular indeterminate color="primary" />
          <span class="text-body-2 text-medium-emphasis">Loading the report…</span>
        </div>
        <ElementsFromHTML v-else-if="validationResultUrl" :rawHtmlURL="validationResultUrl" />
        <!-- Information tied to this dialog's content stays inline, next to
             what it is about (guidelines, "Notifications and alerts"). -->
        <div v-else class="py-4">
          <v-alert
            type="info"
            variant="tonal"
            title="No validation report for this series"
            text="Either the series has never been validated, or an earlier report was removed with its workflow results. Re-run the validation workflow to produce an up-to-date report."
          />
          <v-btn
            class="mt-4"
            color="primary"
            variant="flat"
            :prepend-icon="kaapanaIcons.start"
            @click="runValidationWorkflow(validationResultItem)"
          >
            Re-run validation
          </v-btn>
        </div>
      </v-card-text>
      <v-divider />
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="text" @click="onValidationResultClose">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { notify } from '@kyvg/vue3-notification'
import { apiErrorText, kaapanaApiService } from '@kaapana/base-ui'
import ElementsFromHTML from '@/components/ElementsFromHTML.vue'
import { useDatasetsStore } from '@/stores/datasets'
import { kaapanaIcons, galleryIcons } from '@/utils/galleryIcons'

const emit = defineEmits<{
  runWorkflow: [dag: string, seriesInstanceUID: string | null]
}>()

const datasets_store = useDatasetsStore()

const resultPaths = ref<Record<string, any>>({})
const resultLookupState = ref<Record<string, any>>({})

function onValidationResultClose() {
  datasets_store.setShowValidationResults(false)
  datasets_store.setValidationResultItem(null)
}
async function ensureValidationResultLoaded(resultItemID: string | null) {
  if (!resultItemID) {
    return null
  }

  const cachedResult = resultLookupState.value[resultItemID]
  if (cachedResult && (cachedResult.loading || cachedResult.loaded)) {
    return cachedResult.url
  }

  resultLookupState.value[resultItemID] = {
    loading: true,
    loaded: false,
    found: false,
    url: null,
    object_name: null,
  }

  try {
    const response: any = await kaapanaApiService.kaapanaApiGet(
      '/get-static-website-result-reports',
      { series_id: resultItemID },
    )
    const lookupResult =
      response && response.data && response.data.results && response.data.results[resultItemID]
        ? response.data.results[resultItemID]
        : { found: false, url: null, object_name: null }

    resultLookupState.value[resultItemID] = {
      loading: false,
      loaded: true,
      found: lookupResult.found,
      url: lookupResult.url,
      object_name: lookupResult.object_name,
    }

    if (lookupResult.found && lookupResult.url) {
      resultPaths.value[resultItemID] = lookupResult.url
    } else if (resultItemID in resultPaths.value) {
      delete resultPaths.value[resultItemID]
    }

    return lookupResult.url
  } catch (error: any) {
    notify({
      title: 'Validation report not loaded',
      text: apiErrorText(error, 'The validation report for this series could not be loaded.'),
      type: 'error',
    })
    // Don't cache the failure as "loaded, not found" — a retry must refetch.
    delete resultLookupState.value[resultItemID]
    if (resultItemID in resultPaths.value) {
      delete resultPaths.value[resultItemID]
    }
    return null
  }
}
function invalidateValidationResultCache(resultItemID: string | null) {
  if (!resultItemID) {
    return
  }

  if (resultItemID in resultLookupState.value) {
    delete resultLookupState.value[resultItemID]
  }
  if (resultItemID in resultPaths.value) {
    delete resultPaths.value[resultItemID]
  }
}
function runValidationWorkflow(resultItemID: string | null) {
  invalidateValidationResultCache(resultItemID)
  onValidationResultClose()
  emit('runWorkflow', 'validate-dicoms', resultItemID)
}
function deleteValidationResult(resultItemID: string | null) {
  invalidateValidationResultCache(resultItemID)
  onValidationResultClose()
  emit('runWorkflow', 'clear-validation-results', resultItemID)
}
async function downloadValidationResult(resultItemID: string | null) {
  const resultUri = await ensureValidationResultLoaded(resultItemID)
  if (!resultUri) {
    notify({
      title: 'Nothing to download',
      text: 'No validation report exists for this series. Re-run the validation workflow to produce one.',
      type: 'warn',
    })
    return
  }
  const link: HTMLAnchorElement | null = document.createElement('a')
  link.download = resultItemID + '.html'
  link.href = resultUri
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const validationResultItem = computed(() => datasets_store.validationResultItem)
const validationResultLookup = computed(() => {
  if (!validationResultItem.value) {
    return {
      loading: false,
      loaded: false,
      found: false,
      url: null,
      object_name: null,
    }
  }

  return (
    resultLookupState.value[validationResultItem.value] || {
      loading: false,
      loaded: false,
      found: false,
      url: null,
      object_name: null,
    }
  )
})
const validationResultUrl = computed(() => validationResultLookup.value.url)

watch(validationResultItem, (value) => {
  if (value) {
    ensureValidationResultLoaded(value)
  }
})
</script>

<style scoped>
/* The validation report ships its CSS in <head>, which ElementsFromHTML
   strips, and otherwise relies on Vuetify 2 global classes (.row/.col-*,
   .error/.warning) that no longer exist in Vuetify 3 — mirror them here. */
:deep(.container h1) {
  font-size: 24px;
  margin-bottom: 20px;
}

:deep(.container .attribute) {
  font-size: 18px;
  margin-bottom: 8px;
}

:deep(.validation-item.row) {
  display: flex;
  flex-wrap: wrap;
  margin: -12px;
}

:deep(.validation-item .col) {
  padding: 12px;
}

:deep(.validation-item .col-2) {
  flex: 0 0 15%;
  max-width: 15%;
}

:deep(.validation-item .col-10) {
  flex: 0 0 78%;
  max-width: 78%;
}

:deep(.item-label.error),
:deep(.item-count-label.error) {
  color: rgb(var(--v-theme-on-error));
  background: rgb(var(--v-theme-error));
}

:deep(.item-label.warning),
:deep(.item-count-label.warning) {
  color: rgb(var(--v-theme-on-warning));
  background: rgb(var(--v-theme-warning));
}

:deep(.item-label) {
  line-height: 20px;
  max-width: 100%;
  outline: none;
  overflow: hidden;
  padding: 2px 12px;
  position: relative;
  border-radius: 12px;
  margin-right: 4px;
  text-align: center;
}

:deep(.item-count-label) {
  padding: 2px 16px;
  border-radius: 15px;
  margin-left: 8px;
}

:deep(.incomplete-alert) {
  padding: 16px;
  background-color: rgb(var(--v-theme-error));
  color: rgb(var(--v-theme-on-error));
  margin-bottom: 8px;
  border-radius: 8px;
}
:deep(.hidden) {
  display: none;
}
</style>
