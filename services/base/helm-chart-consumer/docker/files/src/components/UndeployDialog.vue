<template>
  <ConfirmDialog
    :model-value="modelValue"
    :title="`Undeploy “${app?.name ?? ''}”?`"
    :text="text"
    confirm-text="Undeploy"
    color="error"
    @update:model-value="emit('update:modelValue', $event)"
    @confirm="confirm"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ConfirmDialog } from '@kaapana/base-ui'
import { useMockStore } from '@/stores/mock'
import type { DeployedApp } from '@/mock/types'

const props = defineProps<{ modelValue: boolean; app: DeployedApp | null }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; undeployed: [] }>()
const mock = useMockStore()

const text = computed(() => {
  const app = props.app
  if (!app) return ''
  const key = mock.versionOf(app).workspaceParam
  const volume = key
    ? `Its workspace volume (${Number(app.values[key])} GiB) is deleted with all data on it.`
    : 'Its persistent volumes, if it has any, are deleted with all data on them.'
  return `This stops ${app.name} ${mock.scopePhrase(app.scope)} and removes it. ${volume} Data that was not saved to the project storage is lost.`
})

function confirm() {
  if (!props.app) return
  mock.undeploy(props.app.id)
  emit('undeployed')
}
</script>
