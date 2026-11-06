<template>
  <span class="d-inline-flex flex-wrap ga-1">
    <v-chip :color="look.color" size="small" variant="tonal">
      <v-progress-circular v-if="look.busy" indeterminate size="12" width="2" class="mr-2" />
      <v-icon v-else start :icon="look.icon" />
      {{ look.label }}
    </v-chip>
    <v-tooltip v-if="app.drift" location="top" :text="driftText">
      <template #activator="{ props: activator }">
        <v-chip v-bind="activator" color="warning" size="small" variant="tonal" tabindex="0">
          <v-icon start :icon="kaapanaIcons.warning" />
          {{ app.drift.kind === 'changed' ? 'Changed outside Kaapana' : 'Removed outside Kaapana' }}
        </v-chip>
      </template>
    </v-tooltip>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { kaapanaIcons } from '@kaapana/base-ui'
import type { DeployedApp } from '@/mock/types'

const props = defineProps<{ app: DeployedApp }>()

// Colour always comes with an icon and a word, never alone.
const look = computed(() => {
  switch (props.app.state) {
    case 'READY':
      return { label: 'Ready', color: 'success', icon: kaapanaIcons.success, busy: false }
    case 'FAILED':
      return { label: 'Failed', color: 'error', icon: kaapanaIcons.error, busy: false }
    case 'DEPLOYING':
      return { label: 'Deploying', color: 'info', icon: '', busy: true }
    case 'UPDATING':
      return { label: 'Updating', color: 'info', icon: '', busy: true }
    case 'UNDEPLOYING':
      return { label: 'Undeploying', color: undefined, icon: '', busy: true }
    default:
      return { label: props.app.state, color: undefined, icon: kaapanaIcons.info, busy: false }
  }
})

const driftText = computed(() => {
  const d = props.app.drift
  if (!d) return ''
  return d.kind === 'changed'
    ? `The helm release is at revision ${d.revision}; Kaapana deployed revision ${d.recordedRevision}.`
    : 'The helm release no longer exists in the cluster.'
})
</script>
