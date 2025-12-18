<script setup lang="ts">
import { ref } from 'vue'
interface ArtifactListItem {
  key: string
  id: string
  filename: string
  contentType: string
  sizeBytes: number | null
  url: string
}

defineProps<{
  artifactItems: ArtifactListItem[]
  formatArtifactSize: (size?: number | null) => string
}>()

const previewDialog = ref(false)
const previewUrl = ref('')
const previewTitle = ref('')

function buildPreviewUrl(url: string): string {
  return url.includes('?') ? `${url}&disposition=inline` : `${url}?disposition=inline`
}

function openPreview(artifact: ArtifactListItem) {
  previewUrl.value = buildPreviewUrl(artifact.url)
  previewTitle.value = `Preview ${artifact.filename || artifact.id}`
  previewDialog.value = true
}

function closePreview() {
  previewDialog.value = false
  previewUrl.value = ''
  previewTitle.value = ''
}
</script>

<template>
  <div>
    <v-table v-if="artifactItems.length" density="comfortable" class="artifact-table">
      <thead>
        <tr>
          <th class="text-left">Metadata Key</th>
          <th class="text-left">Artifact ID</th>
          <th class="text-left">Filename</th>
          <th class="text-left">Content Type</th>
          <th class="text-left">Size</th>
          <th class="text-left">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="artifact in artifactItems" :key="`${artifact.key}-${artifact.id}`">
          <td>{{ artifact.key }}</td>
          <td class="font-mono">{{ artifact.id }}</td>
          <td>{{ artifact.filename }}</td>
          <td>{{ artifact.contentType }}</td>
          <td>{{ formatArtifactSize(artifact.sizeBytes) }}</td>
          <td>
            <div class="d-flex" style="gap: 8px">
              <v-btn
                variant="text"
                size="small"
                color="secondary"
                @click="openPreview(artifact)"
              >
                <v-icon start>mdi-eye-outline</v-icon>
                Preview
              </v-btn>
              <v-btn
                variant="text"
                size="small"
                color="primary"
                :href="artifact.url"
                target="_blank"
                rel="noopener"
              >
                <v-icon start>mdi-download</v-icon>
                Download
              </v-btn>
            </div>
          </td>
        </tr>
      </tbody>
    </v-table>
    <v-empty-state
      v-else
      icon="mdi-paperclip-off"
      title="No artifacts yet"
      text="Artifacts associated with metadata entries will appear here."
    />

    <v-dialog v-model="previewDialog" max-width="900">
      <v-card>
        <v-card-title class="d-flex align-center justify-space-between">
          <span>{{ previewTitle }}</span>
          <v-btn icon="mdi-close" variant="text" density="comfortable" @click="closePreview" />
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-0">
          <template v-if="previewUrl">
            <iframe
              :key="previewUrl"
              :src="previewUrl"
              class="preview-frame"
              sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-downloads"
            ></iframe>
          </template>
          <div v-else class="pa-6 text-medium-emphasis text-caption">No preview available.</div>
        </v-card-text>
      </v-card>
    </v-dialog>
  </div>
</template>

<style scoped>
.artifact-table th {
  font-weight: 800;
}

.artifact-table td,
.artifact-table th {
  padding: 12px;
}

.preview-frame {
  width: 100%;
  min-height: 70vh;
  border: none;
}

.artifact-table .font-mono {
  font-family: 'Fira Code', 'SFMono-Regular', Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}
</style>
