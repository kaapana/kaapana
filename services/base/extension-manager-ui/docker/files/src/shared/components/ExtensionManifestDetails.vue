<script setup lang="ts">
import { computed, ref } from 'vue'
import DetailMetaLine from '@/shared/components/DetailMetaLine.vue'
import type { ExtensionManifest } from '@/shared/types/apiSchemas'

const props = defineProps<{
  extensionManifest: ExtensionManifest
}>()

const extensionManifestJson = computed(() => JSON.stringify(props.extensionManifest, null, 2))

const extensionManifestDependenciesJson = computed(() =>
  JSON.stringify(props.extensionManifest.dependencies, null, 2),
)

const showingRawManifest = ref(false)

function toggleRawManifest() {
  showingRawManifest.value = !showingRawManifest.value
}
</script>

<template>
  <div class="d-flex flex-column ga-4">
    <div>
      <div class="text-title text-medium-emphasis">Manifest</div>
      <div class="text-body-2">
        {{ props.extensionManifest.name }} {{ props.extensionManifest.version }}
      </div>
    </div>

    <div>
      <div class="text-caption text-medium-emphasis mb-1">Manifest contents</div>
      <div v-if="props.extensionManifest.contents.length" class="d-flex flex-column ga-2">
        <v-card
          v-for="manifestContent in props.extensionManifest.contents"
          :key="`${manifestContent.contentType}:${manifestContent.name}`"
          variant="outlined"
        >
          <v-card-text>
            <DetailMetaLine
              class="text-body-2"
              :items="[manifestContent.name, manifestContent.contentType]"
            />
            <div class="text-caption text-medium-emphasis">
              {{
                manifestContent.files.length === 1
                  ? '1 file'
                  : `${manifestContent.files.length} files`
              }}
            </div>

            <div v-if="manifestContent.files.length" class="d-flex flex-column ga-1 mt-2">
              <div
                v-for="contentFile in manifestContent.files"
                :key="contentFile.path"
                class="text-caption text-medium-emphasis"
              >
                {{ contentFile.path }}
              </div>
            </div>
          </v-card-text>
        </v-card>
      </div>
      <div v-else class="text-body-2 text-medium-emphasis">No manifest contents returned.</div>
    </div>

    <div>
      <div class="text-caption text-medium-emphasis mb-1">Dependencies</div>
      <v-card variant="outlined">
        <v-card-text>
          <pre class="manifest-json text-body-2">{{ extensionManifestDependenciesJson }}</pre>
        </v-card-text>
      </v-card>
    </div>

    <div>
      <div class="d-flex align-center justify-space-between ga-2 mb-1">
        <div class="text-caption text-medium-emphasis">Raw manifest</div>

        <v-btn variant="text" size="small" @click="toggleRawManifest">
          {{ showingRawManifest ? 'Hide' : 'Show' }}
        </v-btn>
      </div>

      <v-card v-if="showingRawManifest" variant="outlined">
        <v-card-text>
          <pre class="manifest-json text-body-2">{{ extensionManifestJson }}</pre>
        </v-card-text>
      </v-card>
    </div>
  </div>
</template>

<style scoped>
.manifest-json {
  color: inherit;
  margin: 0;
  overflow-x: auto;
  white-space: pre-wrap;
}
</style>
