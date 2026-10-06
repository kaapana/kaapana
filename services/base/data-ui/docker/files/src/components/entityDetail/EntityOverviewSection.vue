<script setup lang="ts">
import { computed } from 'vue'
import { buildArtifactUrl } from '@/services/api'
import type { DataEntity } from '@/types/domain'
import { formatDateTime } from '@/utils/format'
import { icons } from '@/utils/icons'

const props = defineProps<{ entity: DataEntity }>()
const emit = defineEmits<{ (e: 'navigate', id: string): void }>()

const thumbnailUrl = computed(() => {
  for (const entry of props.entity.metadata) {
    const artifact = entry.artifacts.find((item) => item.content_type?.startsWith('image/'))
    if (artifact) {
      return buildArtifactUrl(props.entity.id, entry.key, artifact.id)
    }
  }
  return null
})
</script>

<template>
  <div class="overview">
    <v-img
      v-if="thumbnailUrl"
      :src="thumbnailUrl"
      :alt="`Preview of entity ${entity.id}`"
      height="180"
      cover
      class="rounded bg-surface-light"
    />
    <div v-else class="thumb-placeholder rounded bg-surface-light text-medium-emphasis">
      <v-icon :icon="icons.noImage" size="40" />
      <span class="text-body-2">No preview</span>
    </div>
    <dl class="facts text-body-2">
      <dt class="text-medium-emphasis">Created</dt>
      <dd>{{ formatDateTime(entity.created_at) }}</dd>
      <dt class="text-medium-emphasis">Parent</dt>
      <dd>
        <a
          v-if="entity.parent_id"
          href="#"
          class="text-primary"
          @click.prevent="emit('navigate', entity.parent_id)"
        >
          {{ entity.parent_id }}
        </a>
        <span v-else>None</span>
      </dd>
      <dt class="text-medium-emphasis">Children</dt>
      <dd>{{ entity.child_ids?.length ?? 0 }}</dd>
      <dt class="text-medium-emphasis">Storage locations</dt>
      <dd>{{ entity.storage_coordinates.length }}</dd>
    </dl>
  </div>
</template>

<style scoped>
.overview {
  display: grid;
  grid-template-columns: minmax(200px, 260px) 1fr;
  gap: 24px;
  align-items: start;
}

@media (max-width: 700px) {
  .overview {
    grid-template-columns: 1fr;
  }
}

.thumb-placeholder {
  height: 180px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.facts {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 4px 16px;
  margin: 0;
}

.facts dd {
  margin: 0;
  word-break: break-all;
}
</style>
