<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import NavDrawer from '@/components/NavDrawer.vue'
import UnsavedChangesDialog from '@/components/UnsavedChangesDialog.vue'
import ViewUnavailableDialog from '@/components/ViewUnavailableDialog.vue'
import { useAuthStore } from '@/stores/auth'
import { useMenuStore, NO_SECTION } from '@/stores/menu'
import { useProjectStore, projectSlug, withProjectSlug } from '@/stores/project'
import { useSettingsStore } from '@/stores/settings'
import { useNotificationsStore } from '@/stores/notifications'
import { useViewStateStore } from '@/stores/viewState'
import { useIdleLogout } from '@/composables/useIdleLogout'

const auth = useAuthStore()
const menu = useMenuStore()
const project = useProjectStore()
const settings = useSettingsStore()
const notificationsStore = useNotificationsStore()
const viewState = useViewStateStore()
const theme = useTheme()
const route = useRoute()
const router = useRouter()
const idleLogout = useIdleLogout()

// Gate the router-view until settings are seeded into localStorage: the
// extracted view containers read localStorage["settings"] synchronously.
const booted = ref(false)

// Shell route a view asked for that the menu cannot offer; drives the dialog.
const unavailableTarget = ref<string | null>(null)

/**
 * Turn a shell route a view asked for into a route the shell can push, or null
 * when the menu has no such entry for this user. Views may address with an
 * optional /project/<id> prefix, the legacy /web prefix, then
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
    theme.global.name.value = dark ? 'kaapanaThemeDark' : 'kaapanaThemeLight'
  },
  { immediate: true },
)

// Badge counts are project-scoped: watching the route (not the store) means
// the URL prefix is committed, so the http interceptor scopes the re-poll.
// reset drops stale counts; `immediate` rescopes the guard's unscoped boot round.
watch(() => route.params.project, () => menu.refreshBadges(true), { immediate: true })

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

// postMessage contract with the embedded views (same-origin only): views report
// unsaved state (kaapana:view-dirty) so state-destroying actions can warn, and
// ask the shell to open a view (kaapana:navigate) or switch projects
// (kaapana:project-switch).
window.addEventListener('message', (event) => {
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
  // view-dirty confirm still runs and the shell is not reloaded. Unknown slugs
  // are ignored — the guard would only bounce them back.
  if (event.data?.type === 'kaapana:project-switch') {
    const slug = String(event.data.slug ?? '')
    if (!project.availableProjects.some((p) => projectSlug(p) === slug)) return
    router.push({ path: withProjectSlug(route.path, slug), query: route.query })
  }
})

onMounted(async () => {
  // Armed before anything that can reject: inside the try, a failed boot would
  // silently disarm the session's only inactivity control.
  idleLogout.start()
  try {
    await auth.ensureLoaded()
    await Promise.all([menu.ensureLoaded(), project.ensureLoaded(), settings.ensureLoaded()])
    notificationsStore.connect()
    menu.startPolling()
  } catch (err) {
    console.log('Boot failed', err)
  }
  booted.value = true
})
</script>

<template>
  <v-app>
    <notifications position="bottom right" width="20%" :duration="5000" />
    <NavDrawer v-if="booted" />
    <UnsavedChangesDialog />
    <ViewUnavailableDialog :target="unavailableTarget" @close="unavailableTarget = null" />
    <v-main>
      <router-view v-if="booted" />
    </v-main>
  </v-app>
</template>

<style>
body {
  overflow: hidden;
}
</style>
