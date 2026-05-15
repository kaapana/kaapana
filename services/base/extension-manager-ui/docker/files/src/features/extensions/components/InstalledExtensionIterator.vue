<script setup lang="ts">
import type { InstalledExtension } from '@/shared/types/apiSchemas'
import type { RepositoryDict } from '@/features/repositories/types'
import BaseCardIterator from '@/shared/components/BaseCardIterator.vue'
import DetailMetaLine from '@/shared/components/DetailMetaLine.vue'

const props = defineProps<{
  installedExtensions: InstalledExtension[]
  repositories: RepositoryDict
  loadingInstalledExtensions: boolean
  installedExtensionsError?: string | null
}>()

defineEmits<{
  (event: 'selectInstalledExtension', installedExtension: InstalledExtension): void
}>()
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
      <v-card-title>{{ slotProps.item.manifest.name }}</v-card-title>
      <v-card-subtitle>
        <DetailMetaLine
          :items="[slotProps.item.manifest.version, slotProps.item.tag]"
          style="justify-content: center"
        />
      </v-card-subtitle>
      <v-card-text class="d-flex flex-column ga-2">
        <div>
          <v-chip size="small" color="primary" variant="tonal">
            {{ slotProps.item.status }}
          </v-chip>
        </div>
        <div class="text-caption text-medium-emphasis">
          Repository:
          {{
            props.repositories[slotProps.item.repository_id]?.name ?? slotProps.item.repository_id
          }}
        </div>
      </v-card-text>
    </template>
  </BaseCardIterator>
</template>
