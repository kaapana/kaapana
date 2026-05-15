<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import type { ContentStatus, ExtensionManifest, InstalledContent } from '@/shared/types/apiSchemas'

const props = defineProps<{
  extensionManifest: ExtensionManifest
  installedContents?: InstalledContent[]
}>()

const contentStatusColor: Record<ContentStatus, string> = {
  pending: 'warning',
  installing: 'warning',
  installation_failed: 'error',
  installed: 'success',
  uninstalling: 'warning',
  uninstallation_failed: 'error',
  uninstalled: 'grey',
}

function installedContentStatus(name: string, contentType: string): ContentStatus | undefined {
  return props.installedContents?.find(
    (entry) => entry.name === name && entry.content_type === contentType,
  )?.status
}

const extensionManifestJson = computed(() => JSON.stringify(props.extensionManifest, null, 2))

const showingRawManifest = ref(false)
const expandedContents = reactive<Record<string, boolean>>({})
const expandedDependencies = reactive<Record<number, boolean>>({})

function toggleRawManifest() {
  showingRawManifest.value = !showingRawManifest.value
}

function contentKey(name: string, contentType: string): string {
  return `${contentType}:${name}`
}

function toggleContent(name: string, contentType: string) {
  const key = contentKey(name, contentType)
  expandedContents[key] = !expandedContents[key]
}

function isContentExpanded(name: string, contentType: string): boolean {
  return Boolean(expandedContents[contentKey(name, contentType)])
}

function toggleDependency(index: number) {
  expandedDependencies[index] = !expandedDependencies[index]
}

function isDependencyExpanded(index: number): boolean {
  return Boolean(expandedDependencies[index])
}

function dependencyLabel(dep: unknown, index: number): string {
  if (isNamedDependency(dep)) return dep.name
  return `Dependency ${index + 1}`
}

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

function dependencyJson(dep: unknown): string {
  return JSON.stringify(dep, null, 2)
}

const contents = computed(() => props.extensionManifest.contents ?? [])
const dependencies = computed(() => props.extensionManifest.dependencies ?? [])
const contentsLabel = computed(() =>
  contents.value.length === 1 ? '1 item' : `${contents.value.length} items`,
)
const dependenciesLabel = computed(() =>
  dependencies.value.length === 1 ? '1 dependency' : `${dependencies.value.length} dependencies`,
)
</script>

<template>
  <div class="manifest-details">
    <!-- Contents -->
    <section>
      <div class="section-header">
        <div class="section-title">Contents</div>
        <div class="section-count">{{ contentsLabel }}</div>
      </div>

      <div v-if="contents.length" class="content-list">
        <div
          v-for="manifestContent in contents"
          :key="contentKey(manifestContent.name, manifestContent.contentType)"
          class="content-row"
        >
          <button
            type="button"
            class="content-row-header"
            @click="toggleContent(manifestContent.name, manifestContent.contentType)"
          >
            <v-icon size="small">
              {{
                isContentExpanded(manifestContent.name, manifestContent.contentType)
                  ? 'mdi-chevron-down'
                  : 'mdi-chevron-right'
              }}
            </v-icon>
            <span class="content-name">{{ manifestContent.name }}</span>
            <span
              v-if="installedContentStatus(manifestContent.name, manifestContent.contentType)"
              class="content-status"
            >
              <v-icon
                :color="
                  contentStatusColor[
                    installedContentStatus(manifestContent.name, manifestContent.contentType)!
                  ]
                "
                size="x-small"
              >
                mdi-circle
              </v-icon>
              <span>{{
                installedContentStatus(manifestContent.name, manifestContent.contentType)
              }}</span>
            </span>
          </button>

          <div
            v-if="isContentExpanded(manifestContent.name, manifestContent.contentType)"
            class="content-row-body"
          >
            <div class="metadata-grid">
              <div class="metadata-label">Type</div>
              <div class="metadata-value">{{ manifestContent.contentType }}</div>
              <div class="metadata-label">Files</div>
              <div class="metadata-value">
                <div v-if="manifestContent.files.length" class="file-list">
                  <div v-for="file in manifestContent.files" :key="file.path">
                    {{ file.path }}
                  </div>
                </div>
                <div v-else class="text-medium-emphasis">No files</div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="text-body-2 text-medium-emphasis">No manifest contents returned.</div>
    </section>

    <!-- Dependencies -->
    <section v-if="dependencies.length">
      <div class="section-header">
        <div class="section-title">Dependencies</div>
        <div class="section-count">{{ dependenciesLabel }}</div>
      </div>

      <div class="content-list">
        <div
          v-for="(dep, index) in dependencies"
          :key="index"
          class="content-row"
        >
          <button type="button" class="content-row-header" @click="toggleDependency(index)">
            <v-icon size="small">
              {{ isDependencyExpanded(index) ? 'mdi-chevron-down' : 'mdi-chevron-right' }}
            </v-icon>
            <span class="content-name">{{ dependencyLabel(dep, index) }}</span>
          </button>

          <div v-if="isDependencyExpanded(index)" class="content-row-body">
            <div v-if="isNamedDependency(dep)" class="metadata-grid">
              <div class="metadata-label">Name</div>
              <div class="metadata-value">{{ dep.name }}</div>
              <div class="metadata-label">Version</div>
              <div class="metadata-value">{{ dep.version ?? '—' }}</div>
            </div>
            <pre v-else class="manifest-json text-body-2">{{ dependencyJson(dep) }}</pre>
          </div>
        </div>
      </div>
    </section>

    <!-- Advanced -->
    <section>
      <div class="section-header">
        <div class="section-title">Advanced</div>
      </div>

      <div class="advanced-row">
        <span>Raw manifest</span>
        <v-btn variant="text" size="small" @click="toggleRawManifest">
          {{ showingRawManifest ? 'Hide' : 'Show' }}
        </v-btn>
      </div>

      <v-card v-if="showingRawManifest" variant="outlined" class="raw-manifest-card">
        <v-card-text>
          <pre class="manifest-json raw-manifest-code text-body-2">{{ extensionManifestJson }}</pre>
        </v-card-text>
      </v-card>
    </section>
  </div>
</template>

<style scoped>
.manifest-details {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.section-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 8px;
}

.section-title {
  font-weight: 500;
}

.section-count {
  font-size: 13px;
  opacity: 0.6;
}

.content-list {
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
  overflow: hidden;
}

.content-row + .content-row {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.content-row-header {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 8px 12px;
  background: transparent;
  border: 0;
  text-align: left;
  cursor: pointer;
  color: inherit;
  font: inherit;
}

.content-row-header:hover {
  background: rgba(var(--v-theme-on-surface), 0.04);
}

.content-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.content-status {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  opacity: 0.85;
}

.content-row-body {
  padding: 4px 12px 12px 34px;
}

.metadata-grid {
  display: grid;
  grid-template-columns: 88px 1fr;
  row-gap: 8px;
  column-gap: 12px;
}

.metadata-label {
  opacity: 0.6;
  font-size: 13px;
}

.metadata-value {
  font-size: 13px;
  min-width: 0;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.advanced-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.raw-manifest-card {
  margin-top: 8px;
}

.raw-manifest-code {
  max-height: 320px;
  overflow: auto;
}

.manifest-json {
  color: inherit;
  margin: 0;
  white-space: pre-wrap;
}
</style>
