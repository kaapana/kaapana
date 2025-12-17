<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, provide, ref, watch } from 'vue'
import { RouterView } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useTheme } from 'vuetify'
import { useEntityStore } from '@/stores/entityStore'
import { useLayoutStore } from '@/stores/layoutStore'
import SchemaManager from '@/components/SchemaManager.vue'
import ArtifactPruneCard from './components/ArtifactPruneCard.vue'

const store = useEntityStore()
const layoutStore = useLayoutStore()
const { loading } = storeToRefs(store)
const theme = useTheme()

const THEME_STORAGE_KEY = 'data-service-theme'
const supportsLocalStorage = typeof window !== 'undefined' && 'localStorage' in window
const hotkeyDialog = ref(false)
const maintenanceDialog = ref(false)
const schemasDialog = ref(false)
const selectedSchemaKey = ref<string | null>(null)
const hotkeySearch = ref('')
const hotkeySearchField = ref()
const hotkeyShortcuts = [
  { combo: 'F', description: 'Open entity query builder and focus the chip composer' },
  { combo: '+', description: 'Zoom entities in (show more per row) when the gallery is active' },
  { combo: '-', description: 'Zoom entities out (show fewer per row) when the gallery is active' },
  { combo: 'C', description: 'Copy the current query JSON to the clipboard' },
  { combo: 'P', description: 'Paste query JSON from the clipboard and run it' },
  { combo: 'X', description: 'Reset the current entity query (clears filters and results)' },
  { combo: '?', description: 'Show all keyboard shortcuts' },
]

// Provide schema dialog control to child components
provide('openSchemasDialog', (key?: string) => {
  selectedSchemaKey.value = key ?? null
  schemasDialog.value = true
})

watch(schemasDialog, (isOpen) => {
  if (!isOpen) {
    selectedSchemaKey.value = null
  }
})

const filteredHotkeyShortcuts = computed(() => {
  const query = hotkeySearch.value.trim().toLowerCase()
  if (!query) {
    return hotkeyShortcuts
  }
  return hotkeyShortcuts.filter((shortcut) => {
    return (
      shortcut.combo.toLowerCase().includes(query) ||
      shortcut.description.toLowerCase().includes(query)
    )
  })
})

function shouldIgnoreHotkeyTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false
  }
  const tagName = target.tagName
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(tagName)) {
    return true
  }
  return Boolean(target.isContentEditable)
}

function handleGlobalHotkeys(event: KeyboardEvent) {
  if (event.defaultPrevented) {
    return
  }
  if (shouldIgnoreHotkeyTarget(event.target)) {
    return
  }
  const hasModifier = event.metaKey || event.ctrlKey || event.altKey
  if (!hasModifier && (event.key === '?' || (event.shiftKey && event.key === '/'))) {
    event.preventDefault()
    hotkeyDialog.value = true
    return
  }

  if (!hasModifier && event.key === '+') {
    if (canZoomIn.value) {
      event.preventDefault()
      zoomIn()
    }
    return
  }

  if (!hasModifier && event.key === '-') {
    if (canZoomOut.value) {
      event.preventDefault()
      zoomOut()
    }
    return
  }
}

onMounted(() => {
  if (supportsLocalStorage) {
    if("settings" in localStorage) {
      const settings = JSON.parse(localStorage["settings"]);
      theme.change(settings["darkMode"] ? 'dark' : 'light');
    }
  }
  store.refresh()
  void store.initEventStream()
  window.addEventListener('keydown', handleGlobalHotkeys)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleGlobalHotkeys)
})

watch(
  () => theme.global.name.value,
  (name) => {
    if (supportsLocalStorage) {
      localStorage.setItem(THEME_STORAGE_KEY, name)
    }
  },
)

watch(hotkeyDialog, (isOpen) => {
  if (isOpen) {
    void nextTick(() => hotkeySearchField.value?.focus())
  } else {
    hotkeySearch.value = ''
  }
})

const isDarkTheme = computed(() => theme.global.current.value.dark)

function toggleTheme() {
  const target = isDarkTheme.value ? 'light' : 'dark'
  theme.change(target)
}

const canZoomOut = computed(() => layoutStore.canZoomEntityOut)
const canZoomIn = computed(() => layoutStore.canZoomEntityIn)

function zoomOut() {
  layoutStore.zoomEntities(-1)
}

function zoomIn() {
  layoutStore.zoomEntities(1)
}

function openApiDocs() {
  const apiUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
  const docsUrl = `${apiUrl}/docs`
  window.open(docsUrl, '_blank')
}
</script>

<template>
  <v-app>
    <v-app-bar color="primary" dark flat density="compact">
      <v-toolbar-title class="app-title">
        <div class="d-flex align-center">
          <v-icon size="small" color="primary-darken-2" class="mr-1">mdi-database</v-icon>
          <span class="text-body-1">Data API</span>
        </div>
      </v-toolbar-title>
      <v-spacer></v-spacer>
      <div class="entity-controls">
        <v-btn
          icon="mdi-refresh"
          :loading="loading"
          @click="store.refresh()"
        ></v-btn>
        <div class="zoom-controls">
          <v-btn-group variant="tonal" density="compact" divided>
            <v-btn
              icon="mdi-magnify-minus-outline"
              :disabled="!canZoomOut"
              :title="canZoomOut ? 'Show fewer entities per row' : 'Minimum zoom reached'"
              @click="zoomOut()"
            ></v-btn>
            <v-btn
              icon="mdi-magnify-plus-outline"
              :disabled="!canZoomIn"
              :title="canZoomIn ? 'Show more entities per row' : 'Maximum zoom reached'"
              @click="zoomIn()"
            ></v-btn>
          </v-btn-group>
        </div>
      </div>
      <v-tooltip text="Metadata Schemas" location="bottom">
        <template #activator="{ props }">
          <v-btn class="ml-1" icon variant="text" v-bind="props" @click="schemasDialog = true">
            <v-icon>mdi-file-document-multiple-outline</v-icon>
          </v-btn>
        </template>
      </v-tooltip>
      <v-tooltip text="API Documentation" location="bottom">
        <template #activator="{ props }">
          <v-btn class="ml-1" icon variant="text" v-bind="props" @click="openApiDocs">
            <v-icon>mdi-api</v-icon>
          </v-btn>
        </template>
      </v-tooltip>
      <v-tooltip text="Hotkeys" location="bottom">
        <template #activator="{ props }">
          <v-btn class="ml-1" icon variant="text" v-bind="props" @click="hotkeyDialog = true">
            <v-icon>mdi-keyboard-outline</v-icon>
          </v-btn>
        </template>
      </v-tooltip>
      <v-tooltip text="Maintenance" location="bottom">
        <template #activator="{ props }">
          <v-btn
            class="ml-1"
            icon
            variant="text"
            v-bind="props"
            @click="maintenanceDialog = true"
          >
            <v-icon>mdi-cog-outline</v-icon>
          </v-btn>
        </template>
      </v-tooltip>
      <v-btn
        class="ml-1"
        icon
        variant="text"
        :title="isDarkTheme ? 'Switch to light mode' : 'Switch to dark mode'"
        @click="toggleTheme"
      >
        <v-icon>{{ isDarkTheme ? 'mdi-white-balance-sunny' : 'mdi-weather-night' }}</v-icon>
      </v-btn>
    </v-app-bar>

    <v-main class="app-main">
      <v-container class="py-3 app-shell" fluid>
        <RouterView />
      </v-container>
    </v-main>
    <v-dialog v-model="hotkeyDialog" max-width="480">
      <v-card>
        <v-card-title class="d-flex align-center justify-space-between py-2">
          <span class="text-body-1">Keyboard shortcuts</span>
          <v-btn icon="mdi-close" variant="text" density="comfortable" @click="hotkeyDialog = false" />
        </v-card-title>
        <v-card-text class="py-2">
          <div class="d-flex align-center flex-wrap" style="gap: 8px">
            <v-text-field
              ref="hotkeySearchField"
              v-model="hotkeySearch"
              variant="outlined"
              density="compact"
              hide-details
              clearable
              placeholder="Search shortcuts"
              prepend-inner-icon="mdi-magnify"
              style="min-width: 200px; flex: 1"
            />
            <div class="shortcut-count text-caption text-medium-emphasis">
              {{ filteredHotkeyShortcuts.length }}/{{ hotkeyShortcuts.length }}
            </div>
          </div>
        </v-card-text>
        <v-divider />
        <v-list density="compact" class="py-0">
          <template v-if="filteredHotkeyShortcuts.length">
            <v-list-item v-for="shortcut in filteredHotkeyShortcuts" :key="shortcut.combo" class="shortcut-item">
              <v-list-item-title class="text-caption">
                <v-chip size="small" color="primary" variant="tonal" class="shortcut-chip">
                  {{ shortcut.combo }}
                </v-chip>
                <span class="ml-3">{{ shortcut.description }}</span>
              </v-list-item-title>
            </v-list-item>
          </template>
          <template v-else>
            <v-list-item>
              <v-list-item-title class="text-caption">No shortcuts match "{{ hotkeySearch }}".</v-list-item-title>
            </v-list-item>
          </template>
        </v-list>
      </v-card>
    </v-dialog>
    <v-dialog v-model="maintenanceDialog" max-width="720">
      <v-card>
        <v-card-title class="d-flex align-center justify-space-between py-2">
          <span class="text-body-1">Maintenance</span>
          <v-btn icon="mdi-close" variant="text" density="comfortable" @click="maintenanceDialog = false" />
        </v-card-title>
        <v-divider />
        <v-card-text class="py-3">
          <ArtifactPruneCard />
        </v-card-text>
      </v-card>
    </v-dialog>
    <v-dialog v-model="schemasDialog" max-width="1000" fullscreen-breakpoint="md">
      <v-card>
        <v-card-title class="d-flex align-center justify-space-between py-2">
          <span class="text-body-1">Metadata Schemas</span>
          <v-btn icon="mdi-close" variant="text" density="comfortable" @click="schemasDialog = false" />
        </v-card-title>
        <v-divider />
        <v-card-text class="py-3">
          <SchemaManager :initial-key="selectedSchemaKey" />
        </v-card-text>
      </v-card>
    </v-dialog>
  </v-app>
</template>

<style scoped>
.app-main {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-shell {
  height: calc(100vh - 48px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

@media (max-width: 600px) {
  .app-shell {
    height: calc(100vh - 48px);
  }
}

.zoom-controls {
  display: flex;
  align-items: center;
}

.entity-controls {
  display: flex;
  align-items: center;
  gap: 4px;
}

.app-title {
  display: flex;
  align-items: center;
  font-weight: 600;
}

.shortcut-chip {
  font-weight: 600;
  min-width: 36px;
  justify-content: center;
}

.shortcut-item {
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  min-height: 36px;
}

.shortcut-item:last-of-type {
  border-bottom: none;
}

.shortcut-count {
  text-align: right;
  white-space: nowrap;
}
</style>
