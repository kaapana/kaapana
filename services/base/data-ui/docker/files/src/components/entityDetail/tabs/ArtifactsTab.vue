<script setup lang="ts">
import { computed, ref } from 'vue'
import { buildArtifactUrl } from '@/services/api'
import type { DataEntity } from '@/types/domain'
import { formatFileSize } from '@/utils/format'
import { icons } from '@/utils/icons'

const props = defineProps<{ entity: DataEntity }>()

interface ArtifactRow {
  key: string
  id: string
  filename: string
  contentType: string
  size: string
  url: string
}

const rows = computed<ArtifactRow[]>(() =>
  props.entity.metadata.flatMap((entry) =>
    entry.artifacts.map((artifact) => ({
      key: entry.key,
      id: artifact.id,
      filename: artifact.filename || artifact.id,
      contentType: artifact.content_type ?? 'Unknown',
      size: formatFileSize(artifact.size_bytes),
      url: buildArtifactUrl(props.entity.id, entry.key, artifact.id),
    })),
  ),
)

const headers = [
  { title: 'File', key: 'filename' },
  { title: 'Metadata entry', key: 'key' },
  { title: 'Type', key: 'contentType' },
  { title: 'Size', key: 'size', align: 'end' as const },
  { title: '', key: 'actions', sortable: false, align: 'end' as const },
]

const preview = ref<ArtifactRow | null>(null)
const previewOpen = ref(false)

function openPreview(row: ArtifactRow) {
  preview.value = row
  previewOpen.value = true
}

function inlineUrl(url: string): string {
  return `${url}?disposition=inline`
}

function isImage(row: ArtifactRow): boolean {
  return row.contentType.startsWith('image/')
}
</script>

<template>
  <div>
    <v-data-table
      v-if="rows.length"
      :headers="headers"
      :items="rows"
      :items-per-page="-1"
      density="compact"
      hide-default-footer
    >
      <template #[`item.actions`]="{ item }">
        <v-btn
          :icon="icons.preview"
          variant="text"
          size="small"
          :aria-label="`Preview ${item.filename}`"
          @click="openPreview(item)"
        />
        <v-btn
          :icon="icons.download"
          variant="text"
          size="small"
          :href="item.url"
          :aria-label="`Download ${item.filename}`"
          download
        />
      </template>
    </v-data-table>
    <p v-else class="text-body-2 text-medium-emphasis">
      The entity has no artifacts. Files attached to its metadata entries appear here.
    </p>

    <v-dialog v-model="previewOpen" max-width="900">
      <v-card v-if="preview" :elevation="5">
        <v-card-title class="d-flex align-center">
          <span class="mr-auto text-truncate">{{ preview.filename }}</span>
          <v-btn
            :icon="icons.close"
            variant="text"
            aria-label="Close"
            @click="previewOpen = false"
          />
        </v-card-title>
        <v-card-text class="pa-0">
          <v-img
            v-if="isImage(preview)"
            :src="inlineUrl(preview.url)"
            :alt="preview.filename"
            max-height="70vh"
            contain
          />
          <iframe
            v-else
            :key="preview.url"
            :src="inlineUrl(preview.url)"
            :title="`Preview of ${preview.filename}`"
            class="preview-frame"
            sandbox="allow-scripts"
          ></iframe>
        </v-card-text>
      </v-card>
    </v-dialog>
  </div>
</template>

<style scoped>
.preview-frame {
  width: 100%;
  height: 70vh;
  border: none;
}
</style>
