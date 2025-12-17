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
  navigateToEntity: (id: string | null | undefined) => void
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
      <div class="hierarchy-summary">
        <div>
          <div class="text-caption text-medium-emphasis">Parent</div>
          <div v-if="entity.parent_id" class="mt-1">
            <v-btn
              size="small"
              variant="text"
              prepend-icon="mdi-arrow-up-bold"
              @click="navigateToEntity(entity.parent_id)"
            >
              {{ entity.parent_id }}
            </v-btn>
          </div>
          <div v-else class="text-body-2 text-medium-emphasis mt-1">No parent entity.</div>
        </div>
        <div>
          <div class="text-caption text-medium-emphasis">
            Children
            <v-chip v-if="entity.child_ids?.length" size="x-small" class="ml-1" variant="tonal">
              {{ entity.child_ids.length }}
            </v-chip>
          </div>
          <div v-if="entity.child_ids?.length" class="hierarchy-chip-group mt-2">
            <v-chip
              v-for="childId in entity.child_ids"
              :key="childId"
              size="small"
              variant="outlined"
              class="hierarchy-chip"
              prepend-icon="mdi-subdirectory-arrow-right"
              @click="navigateToEntity(childId)"
            >
              {{ childId }}
            </v-chip>
          </div>
          <div v-else class="text-body-2 text-medium-emphasis mt-1">No child entities.</div>
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

.hierarchy-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.hierarchy-chip-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hierarchy-chip {
  cursor: pointer;
}
</style>
