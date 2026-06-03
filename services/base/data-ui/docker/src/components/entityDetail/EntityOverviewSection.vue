<script setup lang="ts">
import type { DataEntity } from '@/types/domain'

interface EntityStatsSummary {
  metadata: number
  artifacts: number
  storage: number
}

interface ThumbnailInfo {
  url: string
  filename: string
}

defineProps<{
  entity: DataEntity
  entityStats: EntityStatsSummary
  thumbnailInfo: ThumbnailInfo | null
  formatDateTime: (value?: string | null) => string
}>()
</script>

<template>
  <div class="overview-grid">
    <div class="overview-thumb">
      <v-img
        v-if="thumbnailInfo"
        :src="thumbnailInfo.url"
        :alt="`Thumbnail for ${entity.id}`"
        height="220"
        cover
        class="thumb-image"
      >
        <template #error>
          <div class="thumb-fallback">
            <v-icon size="48">mdi-image-off</v-icon>
            <span>No preview</span>
          </div>
        </template>
      </v-img>
      <div v-else class="thumb-fallback">
        <v-icon size="48">mdi-image-off-outline</v-icon>
        <span>No thumbnail</span>
      </div>
    </div>
    <div class="overview-info">
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-value">{{ entityStats.metadata }}</div>
          <div class="stat-label">Metadata entries</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ entityStats.artifacts }}</div>
          <div class="stat-label">Artifacts</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ entityStats.storage }}</div>
          <div class="stat-label">Storage coordinates</div>
        </div>
      </div>
      <div class="meta-row">
        <div>
          <div class="text-caption text-medium-emphasis">Created</div>
          <div class="text-body-2">{{ formatDateTime(entity.created_at) }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.overview-grid {
  display: grid;
  grid-template-columns: minmax(240px, 320px) 1fr;
  gap: 20px;
}

@media (max-width: 960px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }
}

.overview-thumb {
  border-radius: 16px;
  overflow: hidden;
  background: rgba(var(--v-theme-surface-variant), 0.5);
}

.thumb-image {
  border-radius: 16px;
}

.thumb-fallback {
  min-height: 220px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: rgba(var(--v-theme-on-surface), 0.6);
}

.overview-info {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
}

.stat-card {
  border: 1px solid rgba(var(--v-border-color), 0.6);
  border-radius: 12px;
  padding: 12px 16px;
  background: rgba(var(--v-theme-surface-variant), 0.35);
}

.stat-value {
  font-size: 1.6rem;
  font-weight: 700;
}

.stat-label {
  font-size: 0.85rem;
  color: rgba(var(--v-theme-on-surface), 0.7);
}

.meta-row {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
}
</style>
