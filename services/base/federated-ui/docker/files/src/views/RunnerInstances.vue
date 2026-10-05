<script setup lang="ts">
import { notify } from '@kyvg/vue3-notification'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { apiErrorInfo, apiErrorText, type ApiErrorInfo } from '@kaapana/base-ui'
import { checkForRemoteUpdates, listInstances, type KaapanaInstance } from '@/api/federation'
import AddRemoteInstance from '@/components/AddRemoteInstance.vue'
import InstanceCard from '@/components/InstanceCard.vue'
import { clearDirty } from '@/composables/viewDirty'
import { useFailureDetailsStore } from '@/stores/failureDetails'
import { kaapanaIcons } from '@/utils/icons'
import { notifyFailure } from '@/utils/notifyFailure'

const POLL_INTERVAL_MS = 15_000

const failureDetails = useFailureDetailsStore()

const instances = ref<KaapanaInstance[]>([])
const loading = ref(false)
const loadedOnce = ref(false)
const loadError = ref<ApiErrorInfo | null>(null)
const syncing = ref(false)
const addOpen = ref(false)
let pollTimer = 0

const localInstance = computed(() => instances.value.find((instance) => !instance.remote) ?? null)
const remoteInstances = computed(() =>
  instances.value
    .filter((instance) => instance.remote)
    .sort((a, b) => a.instance_name.localeCompare(b.instance_name)),
)

const summaryLine = computed(() => {
  if (!loadedOnce.value) return 'Loading instances…'
  if (loadError.value && instances.value.length === 0) return 'The instances could not be loaded.'
  const count = remoteInstances.value.length
  if (count === 0) return 'This platform does not federate with any remote instance yet.'
  return `This platform federates with ${count} remote ${count === 1 ? 'instance' : 'instances'}.`
})

const LOAD_FAILURE_TEXT = 'The instance list could not be loaded.'
const loadErrorText = ref(LOAD_FAILURE_TEXT)
let reloadPending = false

async function loadInstances() {
  if (loading.value) {
    reloadPending = true
    return
  }
  loading.value = true
  try {
    instances.value = await listInstances()
    loadError.value = null
  } catch (err) {
    loadError.value = apiErrorInfo(err)
    loadErrorText.value = apiErrorText(err, LOAD_FAILURE_TEXT)
  } finally {
    loading.value = false
    loadedOnce.value = true
  }
  if (reloadPending) {
    reloadPending = false
    await loadInstances()
  }
}

function showLoadFailureDetails() {
  if (!loadError.value) return
  failureDetails.show({
    title: 'Could not load the instances',
    text: loadErrorText.value,
    error: loadError.value,
  })
}

async function syncRemotes() {
  syncing.value = true
  try {
    await checkForRemoteUpdates()
    notify({
      type: 'success',
      title: 'Remote instances synced',
      text: 'The latest settings of all remote instances were fetched.',
    })
    await loadInstances()
  } catch (err) {
    notifyFailure(
      'Could not sync the remote instances',
      'At least one remote instance could not be reached. The settings shown may be outdated.',
      err,
    )
  } finally {
    syncing.value = false
  }
}

onMounted(() => {
  loadInstances()
  pollTimer = window.setInterval(loadInstances, POLL_INTERVAL_MS)
})

onBeforeUnmount(() => {
  window.clearInterval(pollTimer)
  clearDirty()
})
</script>

<template>
  <v-container fluid class="text-left federated-view">
    <div class="d-flex flex-wrap align-start justify-space-between ga-4 mb-4">
      <div>
        <h1 class="text-h4">Instance overview</h1>
        <p class="text-body-2 text-medium-emphasis mt-1" data-testid="summary">{{ summaryLine }}</p>
      </div>

      <div class="d-flex flex-wrap ga-2">
        <v-btn
          variant="outlined"
          :prepend-icon="kaapanaIcons.refresh"
          :loading="syncing"
          :disabled="syncing || remoteInstances.length === 0"
          data-testid="sync-remotes"
          @click="syncRemotes"
        >
          Sync remote instances
        </v-btn>
        <v-btn
          color="primary"
          :prepend-icon="kaapanaIcons.add"
          data-testid="add-remote"
          @click="addOpen = true"
        >
          Add remote instance
        </v-btn>
      </div>
    </div>

    <v-alert
      v-if="loadError && instances.length > 0"
      type="warning"
      variant="tonal"
      density="compact"
      class="mb-4"
      data-testid="stale-list-alert"
    >
      Could not refresh the instances — showing the last version that loaded.
      <template #append>
        <v-btn variant="text" size="small" @click="showLoadFailureDetails">Details</v-btn>
      </template>
    </v-alert>

    <v-row v-if="!loadedOnce">
      <v-col v-for="n in 2" :key="n" cols="12" lg="6">
        <v-skeleton-loader type="list-item-avatar-two-line, divider, list-item@6" :elevation="2" />
      </v-col>
    </v-row>

    <v-card v-else-if="loadError && instances.length === 0" :elevation="2">
      <v-empty-state
        :icon="kaapanaIcons.error"
        color="error"
        size="56"
        title="Could not load the instances"
        text="The federation service could not be reached or reported an error. Try again, or contact your administrator if it persists."
        data-testid="load-error"
      >
        <template #actions>
          <v-btn
            color="primary"
            variant="text"
            :prepend-icon="kaapanaIcons.refresh"
            :loading="loading"
            :disabled="loading"
            @click="loadInstances"
          >
            Try again
          </v-btn>
          <v-btn variant="text" @click="showLoadFailureDetails">Details</v-btn>
        </template>
      </v-empty-state>
    </v-card>

    <template v-else>
      <section v-if="localInstance" class="mb-6">
        <h2 class="text-h5 mb-3">This platform</h2>
        <v-row>
          <v-col cols="12" lg="6">
            <InstanceCard :instance="localInstance" @changed="loadInstances" />
          </v-col>
        </v-row>
      </section>

      <section>
        <h2 class="text-h5 mb-3">Remote instances</h2>
        <v-row v-if="remoteInstances.length">
          <v-col v-for="instance in remoteInstances" :key="instance.id" cols="12" lg="6">
            <InstanceCard :instance="instance" @changed="loadInstances" />
          </v-col>
        </v-row>
        <v-card v-else :elevation="2">
          <v-empty-state
            size="56"
            title="No remote instances yet"
            text="Use “Add remote instance” to run workflows on another Kaapana platform. You need its host and token, which its administrator can copy from that platform's instance card."
            data-testid="no-remotes"
          />
        </v-card>
      </section>
    </template>

    <AddRemoteInstance v-model="addOpen" @added="loadInstances" />
  </v-container>
</template>

<style scoped>
.federated-view {
  max-width: 1600px;
}
</style>
