<script setup lang="ts">
import { computed } from 'vue'
import type { GalleryItem, MetadataEntry } from '@/types/domain'
import { formatValue } from '@/utils/format'
import { icons } from '@/utils/icons'

const props = defineProps<{ item: GalleryItem }>()
const emit = defineEmits<{
  (e: 'view', id: string): void
  (e: 'delete', id: string): void
}>()

const artifactCount = computed(() =>
  props.item.metadata.reduce((sum, meta) => sum + meta.artifacts.length, 0),
)

function metadataSummary(entry: MetadataEntry): string {
  const entries = Object.entries(entry.data ?? {})
  if (!entries.length) {
    return 'No fields'
  }
  return entries
    .slice(0, 2)
    .map(([key, value]) => `${key}: ${formatValue(value)}`)
    .join(' · ')
}

function artifactLabel(entry: MetadataEntry): string {
  const count = entry.artifacts.length
  return count ? `${count} file${count === 1 ? '' : 's'}` : 'No files'
}
</script>

<template>
  <v-card class="entity-card" :elevation="2" data-testid="entity-card">
    <div class="entity-thumb">
      <v-img
        v-if="item.thumbnailUrl"
        :src="item.thumbnailUrl"
        :alt="`Preview of entity ${item.id}`"
        height="200"
        cover
      >
        <template #error>
          <div class="thumb-placeholder bg-surface-light text-medium-emphasis">
            <v-icon :icon="icons.noImage" size="40" />
            <span class="text-body-2">Preview could not be loaded</span>
          </div>
        </template>
      </v-img>
      <div v-else class="thumb-placeholder bg-surface-light text-medium-emphasis">
        <v-icon :icon="icons.noImage" size="40" />
        <span class="text-body-2">No preview</span>
      </div>
    </div>

    <v-card-item>
      <v-card-title class="text-body-1 entity-id">{{ item.id }}</v-card-title>
      <v-card-subtitle>
        {{ item.metadata.length }} metadata entr{{ item.metadata.length === 1 ? 'y' : 'ies' }} ·
        {{ artifactCount }} artifact{{ artifactCount === 1 ? '' : 's' }}
      </v-card-subtitle>
    </v-card-item>

    <v-list density="compact" class="metadata-list py-0">
      <v-list-item
        v-for="meta in item.metadata"
        :key="meta.key"
        :title="meta.key"
        :subtitle="metadataSummary(meta)"
      >
        <template #append>
          <span class="text-caption text-medium-emphasis">{{ artifactLabel(meta) }}</span>
        </template>
      </v-list-item>
    </v-list>

    <v-card-actions>
      <v-btn
        color="primary"
        variant="text"
        :aria-label="`Show details of entity ${item.id}`"
        @click="emit('view', item.id)"
      >
        Details
      </v-btn>
      <v-spacer />
      <v-btn
        :icon="icons.delete"
        variant="text"
        :aria-label="`Delete entity ${item.id}`"
        @click="emit('delete', item.id)"
      />
    </v-card-actions>
  </v-card>
</template>

<style scoped>
.entity-card {
  width: 100%;
  display: flex;
  flex-direction: column;
}

.thumb-placeholder {
  height: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.entity-id {
  word-break: break-all;
  white-space: normal;
}

.metadata-list {
  flex: 1;
  max-height: 180px;
  overflow-y: auto;
}
</style>
