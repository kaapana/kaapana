<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiErrorInfo, kaapanaIcons } from '@kaapana/base-ui'
import { installExtension, fetchExtensions } from '@/features/extensions/api'
import { fetchRepositories, fetchRepositoryExtensionManifests } from '@/features/repositories/api'
import CatalogEntryDialog from '@/features/catalog/components/CatalogEntryDialog.vue'
import CatalogFilterBar from '@/features/catalog/components/CatalogFilterBar.vue'
import type { CatalogEntry, CatalogEntryGroup, CatalogFilters } from '@/features/catalog/types'
import {
  applyCatalogFilters,
  findInstallation,
  groupCatalogEntries,
  hasActiveFilters,
} from '@/features/catalog/utils'
import BaseCardIterator from '@/shared/components/BaseCardIterator.vue'
import DetailMetaLine from '@/shared/components/DetailMetaLine.vue'
import StatusIndicator from '@/shared/components/StatusIndicator.vue'
import { usePolling } from '@/shared/composables/usePolling'
import { useFailureDetailsStore, type FailureDetails } from '@/shared/stores/failureDetails'
import type { InstalledExtension, Repository } from '@/shared/types/apiSchemas'
import { notifyFailure, notifySuccess } from '@/shared/utils/notify'
import { isChanging, plural, presentExtensionStatus } from '@/shared/utils/status'

interface RepositoryFailure {
  repository: Repository
  error: unknown
}

const failureDetails = useFailureDetailsStore()

const repositories = ref<Repository[]>([])
const entries = ref<CatalogEntry[]>([])
const installed = ref<InstalledExtension[]>([])
const loading = ref(false)
const loaded = ref(false)
const loadFailure = ref<FailureDetails | null>(null)
const repositoryFailures = ref<RepositoryFailure[]>([])
const catalogFilters = ref<CatalogFilters>({})

const selectedGroupKey = ref<string | null>(null)
const selectedTag = ref<string | null>(null)
const installing = ref(false)

const catalogEntryGroups = computed(() =>
  groupCatalogEntries(applyCatalogFilters(entries.value, catalogFilters.value)),
)
const allGroups = computed(() => groupCatalogEntries(entries.value))
const selectedGroup = computed(
  () => allGroups.value.find((group) => group.key === selectedGroupKey.value) ?? null,
)
const selectedEntry = computed(
  () => selectedGroup.value?.entries.find((entry) => entry.tag === selectedTag.value) ?? null,
)
const selectedInstallation = computed(() =>
  selectedEntry.value ? findInstallation(selectedEntry.value, installed.value) : undefined,
)

const emptyState = computed(() => {
  if (loadFailure.value) return 'error'
  if (repositories.value.length === 0) return 'no-repositories'
  if (entries.value.length === 0) return 'no-extensions'
  if (hasActiveFilters(catalogFilters.value)) return 'no-matches'
  return 'no-extensions'
})

const repositoryFailureText = computed(() => {
  const names = repositoryFailures.value.map((failure) => `"${failure.repository.name}"`)
  return `Could not load the extensions of ${names.join(', ')}. The catalog shows the other repositories only.`
})

const anyTransitional = computed(() =>
  installed.value.some((extension) => isChanging(extension.status)),
)
usePolling(refreshInstalled, anyTransitional)

function latestInstallation(group: CatalogEntryGroup) {
  for (const entry of group.entries) {
    const installation = findInstallation(entry, installed.value)
    if (installation && installation.status !== 'uninstalled') {
      return {
        version: entry.manifest.version,
        status: presentExtensionStatus(installation.status),
      }
    }
  }
  return null
}

function selectGroup(group: CatalogEntryGroup) {
  selectedGroupKey.value = group.key
  selectedTag.value = group.entries[0]?.tag ?? null
}

function clearSelection() {
  selectedGroupKey.value = null
  selectedTag.value = null
}

function clearFilters() {
  catalogFilters.value = {}
}

function showLoadFailure() {
  if (loadFailure.value) failureDetails.show(loadFailure.value)
}

function showRepositoryFailure() {
  const first = repositoryFailures.value[0]
  if (!first) return
  failureDetails.show({
    title: 'Some repositories could not be loaded',
    text: repositoryFailureText.value,
    error: apiErrorInfo(first.error),
  })
}

async function refreshInstalled() {
  installed.value = await fetchExtensions().catch(() => installed.value)
}

async function loadCatalog() {
  loading.value = true
  loadFailure.value = null

  try {
    const loadedRepositories = await fetchRepositories()
    const [results, loadedInstalled] = await Promise.all([
      Promise.allSettled(
        loadedRepositories.map((repository) => fetchRepositoryExtensionManifests(repository.id)),
      ),
      fetchExtensions().catch(() => installed.value),
    ])
    const loadedEntries: CatalogEntry[] = []
    const failures: RepositoryFailure[] = []
    results.forEach((result, index) => {
      const repository = loadedRepositories[index]!
      if (result.status === 'fulfilled') {
        for (const response of result.value) {
          loadedEntries.push({ repository, tag: response.tag, manifest: response.manifest })
        }
      } else {
        failures.push({ repository, error: result.reason })
      }
    })
    repositories.value = loadedRepositories
    entries.value = loadedEntries
    repositoryFailures.value = failures
    installed.value = loadedInstalled
  } catch (err) {
    loadFailure.value = {
      title: 'Could not load the catalog',
      text: 'The list of repositories could not be loaded from the extension manager.',
      error: apiErrorInfo(err),
    }
    repositories.value = []
    entries.value = []
    repositoryFailures.value = []
  } finally {
    loading.value = false
    loaded.value = true
  }
}

async function installSelectedEntry() {
  const entry = selectedEntry.value
  if (!entry || installing.value) return

  const label = `${entry.manifest.name} ${entry.manifest.version}`
  installing.value = true
  try {
    await installExtension(entry.repository.id, entry.tag)
    notifySuccess(
      'Installation started',
      `${label} is being installed. Follow its progress on the Extensions page.`,
    )
    await refreshInstalled()
  } catch (err) {
    notifyFailure('Installation failed to start', `Could not start installing ${label}.`, err)
  } finally {
    installing.value = false
  }
}

onMounted(loadCatalog)
</script>

<template>
  <div>
    <div class="d-flex flex-wrap align-center justify-space-between ga-3 mb-4">
      <DetailMetaLine
        class="text-body-2 text-medium-emphasis"
        :items="[
          plural(repositories.length, 'repository', 'repositories'),
          plural(entries.length, 'extension version'),
        ]"
      />
      <v-btn
        variant="text"
        color="primary"
        :prepend-icon="kaapanaIcons.refresh"
        :loading="loading"
        :disabled="loading"
        @click="loadCatalog"
      >
        Refresh
      </v-btn>
    </div>

    <v-alert
      v-if="repositoryFailures.length"
      type="warning"
      variant="tonal"
      class="mb-4"
      data-testid="repository-failures"
    >
      {{ repositoryFailureText }}
      <template #append>
        <v-btn variant="text" @click="showRepositoryFailure">Details</v-btn>
      </template>
    </v-alert>

    <CatalogFilterBar
      v-if="entries.length"
      :filters="catalogFilters"
      :repositories="repositories"
      @update:filters="catalogFilters = $event"
    />

    <BaseCardIterator
      :items="catalogEntryGroups"
      :loading="loading || !loaded"
      :item-key="(group) => group.key"
      :card-label="(group) => `Show details of ${group.manifestName} from ${group.repository.name}`"
      @select="selectGroup"
    >
      <template #card="{ item }">
        <v-card-title class="text-wrap">{{ item.manifestName }}</v-card-title>
        <v-card-subtitle>{{ item.repository.name }}</v-card-subtitle>
        <v-card-text class="flex-grow-1 text-body-2 text-medium-emphasis">
          {{ item.repository.repository_url }}
        </v-card-text>
        <v-card-actions class="px-4 text-body-2 text-medium-emphasis">
          <span>{{ plural(item.entries.length, 'version') }}</span>
          <span aria-hidden="true">·</span>
          <span>Latest {{ item.entries[0]?.manifest.version }}</span>
          <v-spacer />
          <template v-if="latestInstallation(item)">
            <StatusIndicator :status="latestInstallation(item)!.status" />
            <span>{{ latestInstallation(item)!.version }}</span>
          </template>
        </v-card-actions>
      </template>

      <template #empty>
        <div data-testid="empty-state">
          <v-empty-state
            v-if="emptyState === 'error'"
            :icon="kaapanaIcons.error"
            color="error"
            size="56"
            title="Could not load the catalog"
            text="The extension manager could not be reached or reported an error. Try again, or contact your administrator if it persists."
          >
            <template #actions>
              <v-btn
                color="primary"
                variant="text"
                :prepend-icon="kaapanaIcons.refresh"
                @click="loadCatalog"
              >
                Try again
              </v-btn>
              <v-btn variant="text" @click="showLoadFailure">Details</v-btn>
            </template>
          </v-empty-state>

          <v-empty-state
            v-else-if="emptyState === 'no-repositories'"
            size="56"
            title="No repositories registered yet"
            text="The catalog lists the extensions published in registered OCI repositories. Add a repository to get started."
          >
            <template #actions>
              <v-btn
                color="primary"
                variant="text"
                :prepend-icon="kaapanaIcons.add"
                to="/repositories"
              >
                Add a repository
              </v-btn>
            </template>
          </v-empty-state>

          <v-empty-state
            v-else-if="emptyState === 'no-matches'"
            :icon="kaapanaIcons.search"
            size="56"
            title="No extensions match the current filters"
            text="The catalog is not empty — the search text and the repository filter exclude every extension in it."
          >
            <template #actions>
              <v-btn color="primary" variant="text" @click="clearFilters">Clear filters</v-btn>
            </template>
          </v-empty-state>

          <v-empty-state
            v-else
            size="56"
            title="No extensions published yet"
            text="None of the registered repositories contains an extension. Publish one with extensionctl, then refresh the catalog."
          >
            <template #actions>
              <v-btn
                color="primary"
                variant="text"
                :prepend-icon="kaapanaIcons.refresh"
                @click="loadCatalog"
              >
                Refresh
              </v-btn>
            </template>
          </v-empty-state>
        </div>
      </template>
    </BaseCardIterator>

    <CatalogEntryDialog
      :group="selectedGroup"
      :entry="selectedEntry"
      :installation="selectedInstallation"
      :installing="installing"
      @close="clearSelection"
      @update:entry="selectedTag = $event.tag"
      @install="installSelectedEntry"
    />
  </div>
</template>
