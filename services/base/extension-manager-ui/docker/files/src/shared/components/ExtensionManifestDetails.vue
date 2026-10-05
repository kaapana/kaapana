<script setup lang="ts">
import { computed } from 'vue'
import StatusIndicator from '@/shared/components/StatusIndicator.vue'
import type { ExtensionManifest, InstalledContent } from '@/shared/types/apiSchemas'
import { plural, presentContentStatus } from '@/shared/utils/status'

const props = defineProps<{
  extensionManifest: ExtensionManifest
  installedContents?: InstalledContent[]
}>()

interface NamedDependency {
  name: string
  version?: string
}

function isNamedDependency(dep: unknown): dep is NamedDependency {
  return (
    typeof dep === 'object' &&
    dep !== null &&
    'name' in dep &&
    typeof (dep as { name: unknown }).name === 'string'
  )
}

function contentKey(name: string, contentType: string): string {
  return `${contentType}:${name}`
}

const installedStatusByKey = computed(() => {
  const statusByKey = new Map<string, string>()
  for (const entry of props.installedContents ?? []) {
    statusByKey.set(contentKey(entry.name, entry.content_type), entry.status)
  }
  return statusByKey
})

const contentRows = computed(() =>
  (props.extensionManifest.contents ?? []).map((content) => {
    const key = contentKey(content.name, content.contentType)
    const status = installedStatusByKey.value.get(key)
    return {
      key,
      name: content.name,
      contentType: content.contentType,
      files: content.files ?? [],
      status: status ? presentContentStatus(status) : null,
    }
  }),
)

const dependencies = computed(() =>
  (props.extensionManifest.dependencies ?? []).map((dep, index) => ({
    key: index,
    label: isNamedDependency(dep) ? dep.name : `Dependency ${index + 1}`,
    named: isNamedDependency(dep) ? dep : null,
    json: JSON.stringify(dep, null, 2),
  })),
)

const extensionManifestJson = computed(() => JSON.stringify(props.extensionManifest, null, 2))
</script>

<template>
  <div class="d-flex flex-column ga-6">
    <section>
      <div class="d-flex align-baseline justify-space-between mb-2">
        <h3 class="text-subtitle-1">Contents</h3>
        <span class="text-caption text-medium-emphasis">{{
          plural(contentRows.length, 'item')
        }}</span>
      </div>
      <v-expansion-panels
        flat
        class="border rounded"
        v-if="contentRows.length"
        multiple
        variant="accordion"
        data-testid="contents"
      >
        <v-expansion-panel v-for="row in contentRows" :key="row.key">
          <v-expansion-panel-title>
            <div class="d-flex align-center flex-wrap ga-3 w-100 me-2">
              <span class="flex-grow-1 text-truncate">{{ row.name }}</span>
              <StatusIndicator v-if="row.status" :status="row.status" class="text-body-2" />
            </div>
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <dl class="manifest-details text-body-2">
              <dt class="text-medium-emphasis">Type</dt>
              <dd>{{ row.contentType }}</dd>
              <dt class="text-medium-emphasis">Files</dt>
              <dd>
                <div v-for="file in row.files" :key="file.path">{{ file.path }}</div>
                <span v-if="row.files.length === 0" class="text-medium-emphasis">No files</span>
              </dd>
            </dl>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
      <p v-else class="text-body-2 text-medium-emphasis">The manifest lists no contents.</p>
    </section>

    <section v-if="dependencies.length">
      <div class="d-flex align-baseline justify-space-between mb-2">
        <h3 class="text-subtitle-1">Dependencies</h3>
        <span class="text-caption text-medium-emphasis">
          {{ plural(dependencies.length, 'dependency', 'dependencies') }}
        </span>
      </div>
      <v-expansion-panels flat class="border rounded" multiple variant="accordion">
        <v-expansion-panel v-for="dep in dependencies" :key="dep.key" :title="dep.label">
          <v-expansion-panel-text>
            <dl v-if="dep.named" class="manifest-details text-body-2">
              <dt class="text-medium-emphasis">Name</dt>
              <dd>{{ dep.named.name }}</dd>
              <dt class="text-medium-emphasis">Version</dt>
              <dd>{{ dep.named.version ?? 'Not specified' }}</dd>
            </dl>
            <pre v-else class="manifest-json text-body-2">{{ dep.json }}</pre>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </section>

    <section>
      <h3 class="text-subtitle-1 mb-2">Advanced</h3>
      <v-expansion-panels flat class="border rounded" variant="accordion">
        <v-expansion-panel title="Raw manifest">
          <v-expansion-panel-text>
            <pre class="manifest-json raw-manifest text-body-2">{{ extensionManifestJson }}</pre>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </section>
  </div>
</template>

<style scoped>
.manifest-details {
  display: grid;
  grid-template-columns: max-content 1fr;
  column-gap: 16px;
  row-gap: 8px;
  margin: 0;
}

.manifest-details dd {
  margin: 0;
  min-width: 0;
  overflow-wrap: anywhere;
}

.manifest-json {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.raw-manifest {
  max-height: 320px;
  overflow: auto;
}
</style>
