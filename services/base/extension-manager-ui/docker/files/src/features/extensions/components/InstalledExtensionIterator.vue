<script setup lang="ts">
import type { InstalledExtension } from '@/shared/types/apiSchemas'
import type { RepositoryDict } from '@/features/repositories/types'
import BaseCardIterator from '@/shared/components/BaseCardIterator.vue'
import { extensionStatusColor } from '@/features/extensions/utils'

const props = defineProps<{
  installedExtensions: InstalledExtension[]
  repositories: RepositoryDict
  loadingInstalledExtensions: boolean
  installedExtensionsError?: string | null
}>()

defineEmits<{
  (event: 'selectInstalledExtension', installedExtension: InstalledExtension): void
}>()

function repositoryName(repositoryId: string): string {
  return props.repositories[repositoryId]?.name ?? repositoryId
}
</script>

<template>
  <BaseCardIterator
    :items="installedExtensions"
    :loading="loadingInstalledExtensions"
    :error="installedExtensionsError"
    empty-message="No extensions currently have platform state."
    :item-key="(extension) => extension.id"
    @select="$emit('selectInstalledExtension', $event)"
  >
    <template v-slot:cardBody="slotProps">
      <div class="installed-card">
        <v-card-title>{{ slotProps.item.manifest.name }}</v-card-title>
        <v-divider />
        <v-card-text class="installed-card-meta">
          <div>{{ slotProps.item.tag }}</div>
          <div class="text-medium-emphasis">
            {{ repositoryName(slotProps.item.repository_id) }}
          </div>
        </v-card-text>
        <v-card-actions class="installed-card-footer text-medium-emphasis">
          <span class="installed-card-status">
            <v-icon :color="extensionStatusColor[slotProps.item.status]" size="x-small">mdi-circle</v-icon>
            <span>{{ slotProps.item.status }}</span>
          </span>
          <span class="installed-card-version">v{{ slotProps.item.manifest.version }}</span>
        </v-card-actions>
      </div>
    </template>
  </BaseCardIterator>
</template>

<style scoped>
.installed-card {
  text-align: left;
}

.installed-card-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.installed-card-footer {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  padding-inline: 16px;
  gap: 6px;
}

.installed-card-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  justify-self: start;
}

.installed-card-version {
  justify-self: end;
}
</style>
