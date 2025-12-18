<script setup lang="ts">
import { computed } from 'vue'
import type { GalleryItem, MetadataEntry } from '@/types/domain'

const props = defineProps<{ item: GalleryItem }>()
const item = computed(() => props.item)
const emit = defineEmits<{
  (e: 'view', id: string): void
  (e: 'delete', id: string): void
}>()

function metadataSummary(entry: MetadataEntry): string {
  const entries = Object.entries(entry.data ?? {})
  if (!entries.length) {
    return 'No structured fields'
  }
  const preview = entries.slice(0, 2).map(([key, value]) => `${key}: ${formatValue(value)}`)
  return preview.join(' · ')
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '—'
  }
  if (typeof value === 'string') {
    return value
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  try {
    return JSON.stringify(value)
  } catch (error) {
    console.error('Failed to stringify metadata value', error)
    return '[object]'
  }
}

function artifactBadge(entry: MetadataEntry): string {
  if (!entry.artifacts.length) {
    return 'no files'
  }
  const imageArtifacts = entry.artifacts.filter((artifact) => artifact.content_type?.startsWith('image/')).length
  if (imageArtifacts === entry.artifacts.length) {
    return `${entry.artifacts.length} image${entry.artifacts.length > 1 ? 's' : ''}`
  }
  return `${entry.artifacts.length} file${entry.artifacts.length > 1 ? 's' : ''}`
}
</script>

<template>
  <v-card class="entity-card" variant="flat">
    <div class="entity-thumb">
      <v-img
        v-if="item.thumbnailUrl"
        :src="item.thumbnailUrl"
        :alt="`Thumbnail for ${item.id}`"
        height="220"
        cover
      >
        <template #error>
          <div class="thumb-fallback">No preview</div>
        </template>
      </v-img>
      <div v-else class="thumb-placeholder">
        <v-icon size="48">mdi-image-off</v-icon>
        <span>No thumbnail</span>
      </div>
      <div class="entity-thumb__overlay">
        <div class="entity-id">{{ item.id }}</div>
        <div class="meta-count">
          {{ item.metadata.length }} metadata ·
          {{ item.metadata.reduce((sum, meta) => sum + meta.artifacts.length, 0) }} artifacts
        </div>
      </div>
    </div>

    <v-card-text>
      <div class="metadata-chips">
        <v-chip
          v-for="meta in item.metadata"
          :key="meta.key"
          size="small"
          variant="tonal"
          color="deep-purple"
          class="mr-1 mb-1"
        >
          <v-icon start size="16">mdi-label</v-icon>
          {{ meta.key }}
        </v-chip>
      </div>

      <v-list density="compact" class="metadata-list">
        <v-list-item v-for="meta in item.metadata" :key="meta.key">
          <template #prepend>
            <v-avatar size="28" color="deep-purple-lighten-4" class="text-uppercase font-weight-medium">
              {{ meta.key.slice(0, 2) }}
            </v-avatar>
          </template>
          <v-list-item-title>{{ meta.key }}</v-list-item-title>
          <v-list-item-subtitle>{{ metadataSummary(meta) }}</v-list-item-subtitle>
          <template #append>
            <v-chip size="x-small" color="grey-darken-1" variant="tonal">{{ artifactBadge(meta) }}</v-chip>
          </template>
        </v-list-item>
      </v-list>
    </v-card-text>

    <v-divider></v-divider>
    <v-card-actions class="justify-space-between">
      <v-btn variant="text" color="primary" @click="emit('view', item.id)">
        <v-icon start>mdi-eye</v-icon>
        View details
      </v-btn>
      <v-btn variant="text" color="error" @click="emit('delete', item.id)">
        <v-icon start>mdi-delete</v-icon>
        Delete
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<style scoped>
.entity-card {
  border-radius: 16px;
  transition: box-shadow 0.2s ease;
  box-shadow: 0 10px 30px rgba(94, 53, 177, 0.08);
}

.entity-card:hover {
  box-shadow: 0 16px 38px rgba(94, 53, 177, 0.18);
}

.entity-thumb {
  position: relative;
  border-radius: 16px 16px 0 0;
  overflow: hidden;
}

.entity-thumb__overlay {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 12px 16px;
  background: linear-gradient(180deg, rgba(0, 0, 0, 0) 0%, rgba(0, 0, 0, 0.7) 100%);
  color: #fff;
}

.entity-thumb__overlay .entity-id {
  font-weight: 600;
  font-size: 1.05rem;
}

.entity-thumb__overlay .meta-count {
  font-size: 0.8rem;
  opacity: 0.85;
}

.thumb-placeholder,
.thumb-fallback {
  height: 220px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(
    135deg,
    rgba(var(--v-theme-primary), 0.15),
    rgba(var(--v-theme-secondary), 0.18)
  );
  color: rgb(var(--v-theme-primary));
  font-weight: 600;
}

.metadata-list {
  max-height: 260px;
  overflow-y: auto;
}

.metadata-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
</style>
