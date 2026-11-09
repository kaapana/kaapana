<template>
  <v-tooltip v-if="look" location="top" :text="look.text">
    <template #activator="{ props: activator }">
      <v-chip v-bind="activator" :color="look.color" size="x-small" variant="tonal" tabindex="0">
        <v-icon start :icon="look.icon" />
        {{ look.label }}
      </v-chip>
    </template>
  </v-tooltip>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { kaapanaIcons } from '@kaapana/base-ui'
import type { DeployedApp } from '@/mock/types'
import { useMockStore } from '@/stores/mock'

const props = defineProps<{ app: DeployedApp }>()
const mock = useMockStore()

const look = computed(() => {
  const status = mock.versionStatus(props.app)
  const { name, version } = props.app
  switch (status.kind) {
    case 'deregistered':
      return {
        label: 'Version no longer registered',
        color: 'warning',
        icon: kaapanaIcons.warning,
        text:
          `Version ${version} is no longer registered. ${name} keeps running and can still be opened and undeployed.` +
          (status.newest ? ` Version ${status.newest} is registered.` : ''),
      }
    case 'newer-registered':
      return {
        label: `${status.newest} registered`,
        color: 'info',
        icon: kaapanaIcons.info,
        text: `A newer version, ${status.newest}, is registered. ${name} stays on ${version}.`,
      }
  }
  return null
})
</script>
