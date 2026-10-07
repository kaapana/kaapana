<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { DataEntity, MetadataEntry } from '@/types/domain'
import { buildArtifactUrl } from '@/services/api'
import EntityOverviewSection from '@/components/entityDetail/EntityOverviewSection.vue'
import MetadataTab from '@/components/entityDetail/tabs/MetadataTab.vue'
import StorageTab from '@/components/entityDetail/tabs/StorageTab.vue'
import HierarchyTab from '@/components/entityDetail/tabs/HierarchyTab.vue'
import ArtifactsTab from '@/components/entityDetail/tabs/ArtifactsTab.vue'

interface EntityStatsSummary {
  metadata: number
  artifacts: number
  storage: number
}

interface ThumbnailInfo {
  url: string
  filename: string
}

interface ArtifactListItem {
  key: string
  id: string
  filename: string
  contentType: string
  sizeBytes: number | null
  url: string
}

const props = defineProps<{ modelValue: boolean; entity: DataEntity | null; loading: boolean }>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'save-metadata', payload: { id: string; entry: MetadataEntry }): void
  (e: 'delete-metadata', payload: { id: string; key: string }): void
  (e: 'delete-entity', id: string): void
  (e: 'navigate-to-entity', id: string): void
}>()

const dialog = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const activeTab = ref<'metadata' | 'storage' | 'hierarchy' | 'artifacts'>('metadata')
const copyToast = ref(false)
const copyToastMessage = ref('')
const copyToastColor = ref<'success' | 'error'>('success')

watch(
  () => props.entity?.id,
  () => {
    activeTab.value = 'metadata'
  },
)

const entityStats = computed<EntityStatsSummary>(() => {
  const entity = props.entity
  if (!entity) {
    return { metadata: 0, artifacts: 0, storage: 0 }
  }
  const artifacts = entity.metadata.reduce((sum, entry) => sum + entry.artifacts.length, 0)
  return {
    metadata: entity.metadata.length,
    artifacts,
    storage: entity.storage_coordinates.length,
  }
})

const thumbnailInfo = computed<ThumbnailInfo | null>(() => {
  const entity = props.entity
  if (!entity) {
    return null
  }
  for (const entry of entity.metadata) {
    const artifact = entry.artifacts.find((item) => item.content_type?.startsWith('image/'))
    if (artifact) {
      return {
        url: buildArtifactUrl(entity.id, entry.key, artifact.id),
        filename: artifact.filename ?? artifact.id,
      }
    }
  }
  return null
})

const artifactItems = computed<ArtifactListItem[]>(() => {
  const entity = props.entity
  if (!entity) {
    return []
  }
  return entity.metadata.flatMap((entry) =>
    entry.artifacts.map((artifact) => ({
      key: entry.key,
      id: artifact.id,
      filename: artifact.filename ?? 'Untitled artifact',
      contentType: artifact.content_type ?? 'unknown',
      sizeBytes: artifact.size_bytes ?? null,
      url: buildArtifactUrl(entity.id, entry.key, artifact.id),
    })),
  )
})

function formatArtifactSize(size?: number | null): string {
  if (size === null || size === undefined) {
    return '—'
  }
  if (size === 0) {
    return '0 B'
  }
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const base = Math.log(size) / Math.log(1024)
  const index = Math.min(units.length - 1, Math.floor(base))
  const value = size / 1024 ** index
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[index]}`
}

function formatDateTime(value?: string | null): string {
  if (!value) {
    return 'Unknown'
  }
  try {
    return new Date(value).toLocaleString()
  } catch (error) {
    console.error('Failed to format date', error)
    return value
  }
}

function formatStorage(storage: DataEntity['storage_coordinates'][number]): string {
  return Object.entries(storage)
    .map(([key, value]) => `${key}: ${String(value)}`)
    .join(' · ')
}

async function copyIdToClipboard() {
  if (!props.entity?.id) {
    return
  }
  const text = props.entity.id
  try {
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
    } else if (typeof document !== 'undefined') {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.append(textarea)
      textarea.focus()
      textarea.select()
      document.execCommand('copy')
      textarea.remove()
    } else {
      throw new Error('Clipboard API unavailable')
    }
    copyToastMessage.value = 'Entity ID copied to clipboard'
    copyToastColor.value = 'success'
  } catch (error) {
    console.error('Failed to copy ID', error)
    copyToastMessage.value = 'Failed to copy ID'
    copyToastColor.value = 'error'
  } finally {
    copyToast.value = true
  }
}

function navigateToEntity(id: string | null | undefined) {
  if (!id) {
    return
  }
  emit('navigate-to-entity', id)
}

function handleDeleteEntity() {
  if (props.entity) {
    emit('delete-entity', props.entity.id)
  }
}

function forwardSaveMetadata(payload: { id: string; entry: MetadataEntry }) {
  emit('save-metadata', payload)
}

function forwardDeleteMetadata(payload: { id: string; key: string }) {
  emit('delete-metadata', payload)
}
</script>

<template>
  <v-dialog v-model="dialog" max-width="1280" close-on-esc>
    <v-card v-if="entity" class="entity-dialog">
      <v-toolbar flat color="surface" class="dialog-toolbar">
        <div class="toolbar-title">
          <div class="toolbar-title__label">Entity ID</div>
          <div class="toolbar-title__value">{{ entity.id }}</div>
        </div>
        <v-spacer></v-spacer>
        <div class="toolbar-actions">
          <v-btn variant="text" color="primary" @click="copyIdToClipboard">
            <v-icon start>mdi-content-copy</v-icon>
            Copy ID
          </v-btn>
          <v-btn variant="text" color="error" :loading="loading" @click="handleDeleteEntity">
            <v-icon start>mdi-delete</v-icon>
            Delete
          </v-btn>
          <v-btn icon="mdi-close" variant="text" @click="dialog = false"></v-btn>
        </div>
      </v-toolbar>

      <v-card-text>
        <EntityOverviewSection
          :entity="entity"
          :entity-stats="entityStats"
          :thumbnail-info="thumbnailInfo"
          :format-date-time="formatDateTime"
          :navigate-to-entity="navigateToEntity"
        />

        <v-tabs v-model="activeTab" class="mt-6 dialog-tabs" color="primary" grow>
          <v-tab value="metadata" prepend-icon="mdi-file-document-outline">
            Metadata
            <v-chip size="x-small" class="ml-2" color="primary" variant="tonal">{{ entityStats.metadata }}</v-chip>
          </v-tab>
          <v-tab value="storage" prepend-icon="mdi-database">
            Storage
            <v-chip size="x-small" class="ml-2" color="primary" variant="tonal">{{ entityStats.storage }}</v-chip>
          </v-tab>
          <v-tab value="hierarchy" prepend-icon="mdi-file-tree">
            Hierarchy
            <v-chip size="x-small" class="ml-2" color="primary" variant="tonal">{{ entity.child_ids?.length ?? 0 }}</v-chip>
          </v-tab>
          <v-tab value="artifacts" prepend-icon="mdi-paperclip">
            Artifacts
            <v-chip size="x-small" class="ml-2" color="primary" variant="tonal">{{ entityStats.artifacts }}</v-chip>
          </v-tab>
        </v-tabs>

        <v-window v-model="activeTab" class="mt-4">
          <v-window-item value="metadata">
            <MetadataTab
              :entity="entity"
              :loading="loading"
              :dialog-open="dialog"
              @save-metadata="forwardSaveMetadata"
              @delete-metadata="forwardDeleteMetadata"
            />
          </v-window-item>

          <v-window-item value="storage">
            <StorageTab :entity="entity" :format-storage="formatStorage" />
          </v-window-item>

          <v-window-item value="hierarchy">
            <HierarchyTab :entity="entity" :navigate-to-entity="navigateToEntity" />
          </v-window-item>

          <v-window-item value="artifacts">
            <ArtifactsTab :artifact-items="artifactItems" :format-artifact-size="formatArtifactSize" />
          </v-window-item>
        </v-window>
      </v-card-text>
    </v-card>

    <v-card v-else>
      <v-card-text class="text-center py-8">
        <v-progress-circular indeterminate color="primary"></v-progress-circular>
      </v-card-text>
    </v-card>
  </v-dialog>

  <v-snackbar v-model="copyToast" :timeout="2500" :color="copyToastColor" multi-line>
    {{ copyToastMessage }}
  </v-snackbar>
</template>

<style scoped>
.entity-dialog {
  border-radius: 18px;
  min-height: 80vh;
}

.dialog-toolbar {
  border-bottom: 1px solid rgba(var(--v-border-color), 0.4);
  padding: 12px 20px;
}

.toolbar-title {
  max-width: 420px;
}

.toolbar-title__label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: rgba(var(--v-theme-on-surface), 0.6);
}

.toolbar-title__value {
  font-weight: 600;
  word-break: break-all;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.dialog-tabs :deep(.v-tab) {
  text-transform: none;
  font-weight: 600;
}
</style>
