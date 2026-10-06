<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import {
  ErrorDetailsDialog,
  KAAPANA_THEME_DARK,
  KAAPANA_THEME_LIGHT,
  apiErrorInfo,
  kaapanaIcons,
} from '@kaapana/base-ui'
import NavDrawer from '@/components/NavDrawer.vue'
import UnsavedChangesDialog from '@/components/UnsavedChangesDialog.vue'
import ViewUnavailableDialog from '@/components/ViewUnavailableDialog.vue'
import { useAuthStore } from '@/stores/auth'
import { useMenuStore, NO_SECTION } from '@/stores/menu'
import { useProjectStore, projectSlug, withProjectSlug } from '@/stores/project'
import { useSettingsStore } from '@/stores/settings'
import { useNotificationsStore } from '@/stores/notifications'
import { useViewStateStore } from '@/stores/viewState'
import { useFailureDetailsStore, type FailureDetails } from '@/stores/failureDetails'
import { useIdleLogout } from '@/composables/useIdleLogout'
import { scopeCurrentRoute } from '@/router'

const auth = useAuthStore()
const menu = useMenuStore()
const project = useProjectStore()
const settings = useSettingsStore()
const notificationsStore = useNotificationsStore()
const viewState = useViewStateStore()
const failureDetails = useFailureDetailsStore()
const theme = useTheme()
const route = useRoute()
const router = useRouter()
const idleLogout = useIdleLogout()

// Gate the router-view until settings are seeded into localStorage: the
// extracted view containers read localStorage["settings"] synchronously.
const booted = ref(false)
// Set when the user could not be loaded. Nothing else can run without the user.
const bootError = ref<FailureDetails | null>(null)

// A failure toast carries its details in `data.failure` (see
// utils/notifyFailure.ts). Selecting the toast opens ErrorDetailsDialog.
function onNotificationClick(item: { data?: unknown }) {
  const failure = (item.data as { failure?: FailureDetails } | undefined)?.failure
  if (failure) failureDetails.show(failure)
}

// Shell route a view asked for that the menu cannot offer; drives the dialog.
const unavailableTarget = ref<string | null>(null)

/**
 * Turn a shell route a view asked for into a route the shell can push, or null
 * when the menu has no such entry for this user. Views address entries by the
 * navigation contract: an optional /project/<id> prefix, the /web prefix, then
 * <section>/<entry> ("-" for a top-level entry, as in /web/-/extensions).
 */
function resolveShellTarget(path: string): string | null {
  const segments = path
    .replace(/^\/project\/[^/]+/, '')
    .replace(/^\/web(?=\/|$)/, '')
    .split('/')
    .filter(Boolean)
  if (segments[0] === NO_SECTION) segments.shift()
  const resolved = menu.resolvePath(segments)
  if (!resolved || !menu.isEntryVisible(resolved.entry)) return null
  if (!project.selectedProject) return null
  const slug = projectSlug(project.selectedProject)
  return slug ? `/project/${slug}/${segments.join('/')}` : null
}

watch(
  () => settings.darkMode,
  (dark) => {
    theme.global.name.value = dark ? KAAPANA_THEME_DARK : KAAPANA_THEME_LIGHT
  },
  { immediate: true },
)

// Badge counts are project-scoped: watching the route (not the store) means
// the URL prefix is committed, so the http interceptor scopes the re-poll.
// reset drops stale counts; `immediate` rescopes the guard's unscoped boot round.
watch(
  () => route.params.project,
  () => menu.refreshBadges(true),
  { immediate: true },
)

// If the selected project vanishes mid-session (deleted / access revoked),
// re-target the current route onto a still-available project. Navigating to
// the fallback leaves availableProjects unchanged, so this cannot loop.
watch(
  () => project.availableProjects,
  (projects) => {
    const sel = project.selectedProject
    if (!sel || projects.some((p) => p.id === sel.id)) return
    // The reload is unavoidable, so clear the dirty flag: the guard must not
    // confirm, and setDirty(false) also dismisses an already-open confirm.
    viewState.setDirty(false)
    const fallback = projects[0]
    if (fallback) {
      router.replace({
        path: withProjectSlug(route.path, projectSlug(fallback)),
        query: route.query,
      })
    } else {
      project.selectedProject = null
      router.replace('/')
    }
  },
)

// postMessage contract with the embedded views, same-origin only; the message
// types and what each one does are listed in README.md.
let lastShellRefresh = 0
window.addEventListener('message', async (event) => {
  if (event.origin !== window.location.origin) return
  if (event.data?.type === 'kaapana:view-dirty') {
    viewState.setDirty(!!event.data.dirty)
  }
  // Resolved against the menu the user can see: a missing or unpermitted entry
  // gets an explicit dialog instead of silently bouncing to the project home.
  if (event.data?.type === 'kaapana:navigate') {
    const target = String(event.data.path ?? '')
    const resolved = resolveShellTarget(target)
    if (resolved) router.push(resolved)
    else unavailableTarget.value = target
  }
  // Via router.push rather than a top-window navigation so the guard's
  // view-dirty confirm still runs and the shell is not reloaded.
  if (event.data?.type === 'kaapana:project-switch') {
    const slug = String(event.data.slug ?? '')
    const isKnown = () => project.availableProjects.some((p) => projectSlug(p) === slug)
    // A just-created project is ahead of the 15s poll: refresh once; what is
    // still unknown is ignored — the guard would only bounce it back.
    if (!isKnown()) await project.refreshProjects()
    if (!isKnown()) return
    router.push({ path: withProjectSlug(route.path, slug), query: route.query })
  }
  // Debounced on the leading edge: senders post from their own polls, and each
  // fresh read costs portal-api a Kubernetes list.
  if (event.data?.type === 'kaapana:shell-refresh') {
    if (Date.now() - lastShellRefresh < 2000) return
    lastShellRefresh = Date.now()
    // A failed refresh keeps the last known menu, as the periodic poll does.
    menu.refresh(true).catch(() => {})
    project.refreshProjects()
  }
})

async function boot() {
  bootError.value = null
  try {
    await auth.ensureLoaded()
  } catch (err) {
    console.error('Boot failed: the user could not be loaded', err)
    bootError.value = {
      title: 'The platform could not start',
      text: 'Your user profile could not be loaded, so the platform cannot start.',
      error: apiErrorInfo(err),
    }
    return
  }
  // After a failed first attempt, the router guard stopped before it added the
  // project to the URL. The settings request below needs the project.
  await scopeCurrentRoute()
  // Each store records its own failure, and the drawer shows it. One failed
  // request must not stop the menu poll or the notification feed.
  await Promise.allSettled([menu.ensureLoaded(), project.ensureLoaded(), settings.ensureLoaded()])
  notificationsStore.connect()
  menu.startPolling()
  booted.value = true
}

onMounted(() => {
  // Started before anything that can fail: a failed boot must not disable the
  // session's only idle logout.
  idleLogout.start()
  boot()
})
</script>

<template>
  <v-app>
    <notifications
      position="bottom right"
      width="20%"
      :duration="5000"
      close-on-click
      @click="onNotificationClick"
    />
    <NavDrawer v-if="booted" />
    <UnsavedChangesDialog />
    <ViewUnavailableDialog :target="unavailableTarget" @close="unavailableTarget = null" />
    <v-main>
      <router-view v-if="booted" />
      <div v-else-if="bootError" class="boot-state">
        <v-empty-state
          :icon="kaapanaIcons.error"
          :title="bootError.title"
          :text="bootError.text"
          size="56"
        >
          <template #actions>
            <v-btn variant="text" @click="failureDetails.show(bootError!)">Details</v-btn>
            <v-btn color="primary" variant="text" @click="boot">Try again</v-btn>
          </template>
        </v-empty-state>
      </div>
      <div v-else class="boot-state" aria-busy="true">
        <v-progress-circular
          indeterminate
          color="primary"
          size="48"
          aria-label="Loading the platform"
        ></v-progress-circular>
      </div>
    </v-main>
    <ErrorDetailsDialog
      v-model="failureDetails.open"
      :title="failureDetails.current?.title"
      :text="failureDetails.current?.text"
      :error="failureDetails.current?.error ?? null"
    />
  </v-app>
</template>

<style>
body {
  overflow: hidden;
}

.boot-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
}
</style>
