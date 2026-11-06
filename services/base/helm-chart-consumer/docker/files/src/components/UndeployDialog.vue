<template>
  <!-- ConfirmDialog takes only a sentence; this one also needs the volume choice (Q5),
       so it repeats ConfirmDialog's contract: 400 px, Cancel focused, Escape cancels. -->
  <v-dialog :model-value="modelValue" max-width="400" @update:model-value="onUpdate" @after-leave="restoreFocus">
    <v-card v-if="app" :elevation="5">
      <v-card-title class="text-wrap">Undeploy "{{ app.name }}"?</v-card-title>
      <v-card-text>
        <p>
          This stops the application and removes it from {{ mock.projectName(app.projectId) }}. Files that were not
          saved to the project storage are lost.
        </p>
        <template v-if="volumeSize !== null">
          <p v-if="mock.options.volumesOnUndeploy === 'delete'" class="mt-3">
            Its workspace volume ({{ volumeSize }} GiB) is deleted too.
          </p>
          <p v-else-if="mock.options.volumesOnUndeploy === 'keep'" class="mt-3">
            Its workspace volume ({{ volumeSize }} GiB) is kept. A Kaapana system admin can delete it later.
          </p>
          <div v-else class="d-flex align-center mt-2">
            <v-checkbox
              v-model="deleteVolume"
              :label="`Also delete the workspace volume (${volumeSize} GiB)`"
              color="error"
              density="compact"
              hide-details
            />
            <StoryRef ids="Q5" />
          </div>
        </template>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn ref="cancelButton" @click="cancel">Cancel</v-btn>
        <v-btn color="error" @click="confirm">Undeploy</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import type { VBtn } from 'vuetify/components'
import { useMockStore } from '@/stores/mock'
import type { DeployedApp } from '@/mock/types'
import StoryRef from './StoryRef.vue'

const props = defineProps<{ modelValue: boolean; app: DeployedApp | null }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; undeployed: [] }>()
const mock = useMockStore()

const deleteVolume = ref(false)
const cancelButton = ref<InstanceType<typeof VBtn> | null>(null)
let opener: HTMLElement | null = null

const volumeSize = computed(() => {
  if (!props.app) return null
  const key = mock.definition(props.app.appId).workspaceParam
  return key ? Number(props.app.values[key]) : null
})

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    deleteVolume.value = false
    opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
    await nextTick()
    cancelButton.value?.$el?.focus()
  },
)

function restoreFocus() {
  if (opener?.isConnected) opener.focus()
  opener = null
}

function onUpdate(value: boolean) {
  emit('update:modelValue', value)
}

function cancel() {
  emit('update:modelValue', false)
}

function confirm() {
  if (!props.app) return
  const option = mock.options.volumesOnUndeploy
  const drop = option === 'delete' || (option === 'ask' && deleteVolume.value)
  mock.undeploy(props.app.id, drop)
  emit('update:modelValue', false)
  emit('undeployed')
}
</script>
