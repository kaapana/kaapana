<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectStore, projectSlug } from '@/stores/project'
import { useViewStateStore } from '@/stores/viewState'
import { useIdleLogout } from '@/composables/useIdleLogout'
import { isKeycloakAuthUrl, reloadForLogin } from '@/api/http'
import { iframeSrcFor, resolveViewEntry } from '@/utils/iframeSrc'
import type { MenuEntry } from '@/types/menu'

const route = useRoute()
const project = useProjectStore()
const viewState = useViewStateStore()
const idleLogout = useIdleLogout()

const iframeRef = ref<HTMLIFrameElement | null>(null)
// Last URL seen inside the iframe, so "refresh" reloads the page the user is
// actually on, not the entry's start page.
const trackedUrl = ref('')

// Entry resolution and src computation live in utils/iframeSrc so the router
// guard can predict whether a navigation would reload the iframe.
const entry = computed<MenuEntry | null>(() => resolveViewEntry(route)?.entry ?? null)

const src = computed(() =>
  iframeSrcFor(route, project.selectedProject ? projectSlug(project.selectedProject) : null),
)

// Only shell-driven src changes show the loader; in-iframe navigation also
// fires @load but never sets loading back to true.
const loading = ref(true)
watch(src, () => {
  loading.value = true
  // A shell-driven navigation/reload replaces the view: it starts clean.
  viewState.setDirty(false)
})

function onLoad() {
  loading.value = false
  // A freshly (re)loaded view has no unsaved changes yet; also covers in-iframe
  // navigation, which never goes through the src watch above.
  viewState.setDirty(false)
  const contentWindow = iframeRef.value?.contentWindow
  if (!contentWindow) return
  try {
    trackedUrl.value = contentWindow.location.href
    // The same-host login redirect (see api/http.ts) can render Keycloak INSIDE
    // the iframe; escape with a full-window reload. A cross-origin Keycloak host
    // lands in the catch below — the login page just stays in the iframe.
    if (isKeycloakAuthUrl(trackedUrl.value)) {
      reloadForLogin()
      return
    }
    // Re-attach on EVERY load: in-iframe navigation replaces the document and
    // drops the activity listeners, which would break the shared idle timer.
    idleLogout.attachActivityListeners(contentWindow.document)
  } catch {
    // Cross-origin iframe content: neither trackable nor idle-monitorable.
  }
}

async function refreshIframe() {
  if (!iframeRef.value || !trackedUrl.value) return
  // Reloading discards the view's in-memory state just like a navigation does;
  // confirm first when the view reported unsaved changes.
  if (!(await viewState.confirmLeave())) return
  loading.value = true
  iframeRef.value.src = trackedUrl.value
}

function openExternalPage() {
  window.open(trackedUrl.value || src.value, '_blank')
}
</script>

<template>
  <div v-if="entry" class="kaapana-iframe-container">
    <iframe
      ref="iframeRef"
      :key="entry.id"
      :src="src"
      class="kaapana-iframe"
      @load="onLoad"
    ></iframe>
    <div v-if="loading" class="iframe-loading">
      <v-progress-circular indeterminate color="primary" size="48" />
    </div>
    <!-- hotspot must precede the overlay: the reveal rule uses a sibling selector -->
    <div class="overlay-hotspot"></div>
    <div class="iframe-overlay">
      <a @click="refreshIframe()">
        <v-icon color="white">mdi-refresh</v-icon>
      </a>
      <a @click="openExternalPage()">
        <v-icon color="white">mdi-open-in-new</v-icon>
      </a>
    </div>
  </div>
  <!-- No entry resolves for this route (empty or unreachable menu, so not even
       a default view exists). Without this the whole main area stays blank. -->
  <div v-else class="no-view">
    <div class="text-h6">No view available</div>
    <div class="text-body-2">The menu has no entry to show — see the sidebar for details.</div>
  </div>
</template>

<style scoped>
.no-view {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  gap: 4px;
  padding: 16px;
  text-align: center;
}

.kaapana-iframe-container {
  /* Anchors the loading overlay and corner controls to the iframe area;
     without it the spinner centers on the viewport, offset by the drawer. */
  position: relative;
  height: 100vh;
}

.kaapana-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

/* z-index stays below the app bar/drawer (and the corner overlay), like the
   iframe it hides. */
.iframe-loading {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgb(var(--v-theme-background));
}

/* Invisible trigger zone in the very corner; small on purpose so the
   controls never cover iframe content unless deliberately sought out. */
.overlay-hotspot {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 24px;
  height: 24px;
  z-index: 2147483647;
}

.iframe-overlay {
  position: absolute;
  bottom: 0;
  right: 0;
  text-align: center;
  background-color: rgba(77, 77, 77, 0.466);
  padding: 2px;
  z-index: 2147483647;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s;
}

.overlay-hotspot:hover ~ .iframe-overlay,
.iframe-overlay:hover {
  opacity: 1;
  pointer-events: auto;
}

.iframe-overlay > a {
  line-height: 0px;
  cursor: pointer;
}

.iframe-overlay > a > i {
  margin: 2px;
}
</style>
