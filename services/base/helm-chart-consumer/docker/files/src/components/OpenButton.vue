<template>
  <v-btn
    v-if="app.state === 'READY'"
    :color="color"
    :variant="variant"
    :size="size"
    :prepend-icon="kaapanaIcons.externalLink"
    :aria-label="`Open ${app.name} in a new tab`"
    @click.stop="mock.openApp(app)"
  >
    Open
  </v-btn>
  <!-- A disabled button gets no pointer events, so the tooltip hangs on a wrapper. -->
  <v-tooltip v-else location="top" :text="reason">
    <template #activator="{ props: activator }">
      <span v-bind="activator" tabindex="0" @click.stop>
        <v-btn :variant="variant" :size="size" :prepend-icon="kaapanaIcons.externalLink" disabled>Open</v-btn>
      </span>
    </template>
  </v-tooltip>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { kaapanaIcons } from '@kaapana/base-ui'
import { useMockStore } from '@/stores/mock'
import type { DeployedApp } from '@/mock/types'

const props = withDefaults(
  defineProps<{ app: DeployedApp; color?: string; variant?: 'outlined' | 'flat' | 'text'; size?: string }>(),
  { color: undefined, variant: 'outlined', size: 'small' },
)
const mock = useMockStore()

const reason = computed(() => {
  const { name, state, drift } = props.app
  if (drift?.kind === 'removed') return `${name} no longer runs: its helm release was removed outside Kaapana.`
  switch (state) {
    case 'DEPLOYING':
      return `${name} is still starting. You can open it when its state is Ready.`
    case 'UPDATING':
      return `${name} is being updated. You can open it when its state is Ready.`
    case 'UNDEPLOYING':
      return `${name} is being undeployed.`
    case 'FAILED':
      return `${name} could not be started. Its details say why.`
    default:
      return ''
  }
})
</script>
