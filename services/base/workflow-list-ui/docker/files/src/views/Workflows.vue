<template>
  <div class="federated-panel">
    <v-container class="text-left" fluid>
      <workflow-table
        :workflows="clientWorkflows"
        :ext-loading="workflowTableLoading"
        :total-items="totalItems"
        @refreshView="() => getClientWorkflows(true)"
        @update:options="onOptions"
      ></workflow-table>
    </v-container>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { useNotification } from '@kyvg/vue3-notification'
import { kaapanaApiService } from '@kaapana/base-ui'
import type { Workflow } from '@/types/workflow'
import WorkflowTable from '@/components/WorkflowTable.vue'

interface WorkflowOptions {
  page: number
  itemsPerPage: number
  search?: string
  [key: string]: any
}

const { notify } = useNotification()

let polling = 0
const clientWorkflows = ref<Workflow[]>([])
const workflowTableLoading = ref(false)
const totalItems = ref(0)
const options = ref<WorkflowOptions>({
  page: 1,
  itemsPerPage: 5,
  search: '',
})

// `userInitiated` is only true for an explicit refresh (the toolbar refresh
// button); the 15s background poll leaves it false so it refreshes silently.
function getClientWorkflows(userInitiated = false) {
  console.log('Fetching workflows')
  workflowTableLoading.value = true
  const { page, itemsPerPage, search } = options.value
  console.log('Search: ', search)
  kaapanaApiService
    .federatedClientApiGet('/workflows', {
      limit: itemsPerPage,
      offset: (page - 1) * itemsPerPage,
      search: search,
    })
    .then((response: any) => {
      workflowTableLoading.value = false
      clientWorkflows.value = response.data[0]
      totalItems.value = response.data[1]
      if (userInitiated) {
        notify({
          title: 'Successfully refreshed workflow list.',
          type: 'success',
        })
      }
    })
    .catch((err: any) => {
      workflowTableLoading.value = false
      notify({
        title: 'Error while refreshing workflow list.',
        type: 'error',
      })
      console.log(err)
    })
}

function onOptions(newOptions: WorkflowOptions) {
  options.value = newOptions
  getClientWorkflows()
}

function clearExtensionsInterval() {
  window.clearInterval(polling)
}

// TODO Workflow list auto-refresh variable exported into settings/config.
function startExtensionsInterval() {
  console.log('Surprise refresh')
  polling = window.setInterval(() => {
    getClientWorkflows()
  }, 15000)
}

onMounted(() => {
  workflowTableLoading.value = true
  startExtensionsInterval()
})

onBeforeUnmount(() => {
  clearExtensionsInterval()
})
</script>

<style lang="scss">
a {
  text-decoration: none;
}

.v-expansion-panel-content__wrap {
  padding: 0;
}

.toggleMouseHand {
  cursor: pointer;
}

.someSpace {
  margin-bottom: 20px;
}
</style>
