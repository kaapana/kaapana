<script setup lang="ts">
import { onMounted, ref } from 'vue'
import http from '@/api/http'
import AboutDialog from '@/components/AboutDialog.vue'
import DevLinksButton from '@/components/DevLinksButton.vue'
import NotificationButton from '@/components/NotificationButton.vue'
import ProjectSelector from '@/components/ProjectSelector.vue'
import SettingsDialog from '@/components/SettingsDialog.vue'
import UserMenu from '@/components/UserMenu.vue'
import { useAuthStore } from '@/stores/auth'
import { useMenuStore } from '@/stores/menu'
import { useProjectStore, projectSlug } from '@/stores/project'
import { useSettingsStore } from '@/stores/settings'
import type { DevLink, MenuEntry, MenuItem } from '@/types/menu'

const auth = useAuthStore()
const menu = useMenuStore()
const project = useProjectStore()
const settings = useSettingsStore()

const mini = ref(false)

const chartVersion = ref('')
onMounted(async () => {
  try {
    const res = await http.get<{ version?: string }>('/jsons/commonData.json')
    // "kaapana-admin-chart:0.7.0-latest | Build-Timestamp: ..." → "0.7.0-latest"
    const chart = res.data.version?.split('|')[0]?.trim() ?? ''
    chartVersion.value = chart.substring(chart.indexOf(':') + 1)
  } catch {
    // header simply omits the version
  }
})

// Project-prefixed so the links match the canonical routes (active-state
// highlighting compares against the current, prefixed URL).
function entryRoute(entry: MenuEntry, section?: string): string {
  const base = section ? `/${section}/${entry.id}` : `/${entry.id}`
  const selected = project.selectedProject
  return selected ? `/project/${projectSlug(selected)}${base}` : base
}

// External (target:'tab') links open the raw ingress path; a "path"-scoped
// entry must still carry the project prefix so it opens in the right scope.
function entryHref(entry: MenuEntry): string {
  const selected = project.selectedProject
  return entry.project === 'path' && selected
    ? `/project/${projectSlug(selected)}${entry.path}`
    : entry.path
}

// Shown on the section header so the count isn't hidden while it's collapsed.
function sectionBadgeCount(item: MenuItem): number {
  if (item.type !== 'section') return 0
  return item.entries.reduce((sum, entry) => sum + menu.badgeCount(entry), 0)
}

// Empty unless dev mode is on — an empty list keeps the #append slot unrendered.
function devLinks(entry: MenuEntry): DevLink[] {
  return settings.devMode ? menu.visibleDevLinks(entry) : []
}

// Stand-in for missing icons in the collapsed rail: "Data Upload" → "DU", "Datasets" → "Dat"
function glyph(label: string): string {
  const words = label.trim().split(/\s+/)
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase()
  return label.slice(0, 3)
}
</script>

<template>
  <v-navigation-drawer permanent :mobile-breakpoint="0" :rail="mini" color="navigation">
    <!-- Deliberately Material blue, NOT the theme primary -->
    <div class="bg-blue py-2 mb-5">
      <div class="d-flex align-center px-2">
        <!-- Brand styled after the kaapana.ai nav-brand: logo + wordmark -->
        <router-link to="/" class="brand d-flex align-center" title="Kaapana">
          <v-avatar color="white" :size="40" class="logo-avatar">
            <v-img src="/assets/img/logo.webp" alt="Kaapana" contain></v-img>
          </v-avatar>
          <span v-if="!mini" class="brand-text">
            <span class="brand-name">Kaapana</span>
            <span v-if="chartVersion" class="brand-version">{{ chartVersion }}</span>
          </span>
        </router-link>
        <v-spacer></v-spacer>
        <!-- comfortable density so brand + three buttons fit the drawer width -->
        <v-defaults-provider v-if="!mini" :defaults="{ VBtn: { density: 'comfortable' } }">
          <SettingsDialog />
          <!-- margins keep the badge clear of its neighbors; land on NotificationButton's root div -->
          <NotificationButton class="mr-3" />
          <UserMenu v-if="auth.isAuthenticated" />
        </v-defaults-provider>
      </div>

      <div v-if="!mini" class="px-2 pt-4">
        <ProjectSelector />
      </div>
    </div>

    <v-list
      v-if="auth.isAuthenticated && menu.visibleItems.length > 0"
      class="nav-menu"
      :class="{ 'nav-menu--rail': mini }"
      density="compact"
      nav
      color="primary"
      open-strategy="single"
    >
      <template v-for="item in menu.visibleItems" :key="item.id">
        <!-- Top-level entries -->
        <v-list-item
          v-if="item.type === 'entry' && item.target === 'iframe'"
          :to="entryRoute(item)"
          :prepend-icon="item.icon"
        >
          <template #title>
            {{ item.label }}
            <v-badge
              v-if="menu.badgeCount(item) > 0"
              :content="menu.badgeCount(item)"
              color="primary"
              inline
            />
          </template>
          <template v-if="devLinks(item).length" #append>
            <DevLinksButton :links="devLinks(item)" />
          </template>
        </v-list-item>
        <v-list-item
          v-else-if="item.type === 'entry'"
          :href="entryHref(item)"
          target="_blank"
          :prepend-icon="item.icon"
          :title="item.label"
        >
          <template v-if="devLinks(item).length" #append>
            <DevLinksButton :links="devLinks(item)" />
          </template>
        </v-list-item>
        <!-- Sections -->
        <v-list-group v-else :value="item.id">
          <template #activator="{ props }">
            <v-list-item v-bind="props" :prepend-icon="item.icon">
              <template #title>
                {{ item.label }}
                <v-badge
                  v-if="sectionBadgeCount(item) > 0"
                  :content="sectionBadgeCount(item)"
                  color="primary"
                  inline
                />
              </template>
            </v-list-item>
          </template>
          <template v-for="entry in item.entries" :key="entry.id">
            <v-list-item
              v-if="entry.target === 'iframe'"
              :to="entryRoute(entry, item.id)"
              :append-icon="entry.icon"
            >
              <template v-if="mini" #prepend>
                <span class="glyph">{{ glyph(entry.label) }}</span>
              </template>
              <template #title>
                {{ entry.label }}
                <v-badge
                  v-if="menu.badgeCount(entry) > 0"
                  :content="menu.badgeCount(entry)"
                  color="primary"
                  inline
                />
              </template>
              <!-- v-icon takes its icon from the slot's defaults provider, so
                   append-icon still renders beside the dev button -->
              <template v-if="devLinks(entry).length" #append>
                <DevLinksButton :links="devLinks(entry)" />
                <v-icon v-if="entry.icon"></v-icon>
              </template>
            </v-list-item>
            <v-list-item
              v-else
              :href="entryHref(entry)"
              target="_blank"
              :title="entry.label"
              :append-icon="entry.icon"
            >
              <template v-if="mini" #prepend>
                <span class="glyph">{{ glyph(entry.label) }}</span>
              </template>
              <template v-if="devLinks(entry).length" #append>
                <DevLinksButton :links="devLinks(entry)" />
                <v-icon v-if="entry.icon"></v-icon>
              </template>
            </v-list-item>
          </template>
        </v-list-group>
      </template>
    </v-list>
    <!-- Gated on emptiness, not menu.error, so a transient poll failure keeps
         showing the last known menu. -->
    <div v-else-if="auth.isAuthenticated" class="px-4 py-2">
      <v-progress-circular v-if="!menu.loaded && !menu.error" indeterminate size="20" />
      <template v-else-if="menu.error">
        <div class="text-subtitle-2">Menu unavailable</div>
        <div class="text-caption">The platform could not be reached. Reload once it is back.</div>
      </template>
      <template v-else>
        <div class="text-subtitle-2">No entries</div>
        <div class="text-caption">
          Nothing is installed, or your roles grant access to none of it.
        </div>
      </template>
    </div>

    <template #append>
      <!-- small buttons keep the footer unobtrusive -->
      <div v-if="!mini" class="d-flex align-center px-1 pt-1 pb-0 ga-2">
        <v-btn icon variant="text" size="small" title="Collapse Sidebar" @click.stop="mini = true">
          <v-icon>mdi-dock-left</v-icon>
        </v-btn>
        <v-spacer></v-spacer>
        <AboutDialog />
        <v-btn icon variant="text" size="small" to="/help" title="Help">
          <v-icon>mdi-help-circle-outline</v-icon>
        </v-btn>
        <v-btn icon variant="text" size="small" title="Log out" @click="auth.requestLogout()">
          <v-icon>mdi-exit-to-app</v-icon>
        </v-btn>
      </div>
      <div v-else class="d-flex flex-column align-center px-1 pt-1 pb-0">
        <v-btn icon variant="text" size="small" title="Expand Sidebar" @click.stop="mini = false">
          <v-icon>mdi-dock-left</v-icon>
        </v-btn>
        <AboutDialog />
        <v-btn icon variant="text" size="small" to="/help" title="Help">
          <v-icon>mdi-help-circle-outline</v-icon>
        </v-btn>
        <v-btn icon variant="text" size="small" title="Log out" @click="auth.requestLogout()">
          <v-icon>mdi-exit-to-app</v-icon>
        </v-btn>
      </div>
    </template>
  </v-navigation-drawer>
</template>

<style scoped>
.brand {
  gap: 8px;
  text-decoration: none;
  min-width: 0;
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.brand-name {
  color: white;
  font-size: 1rem;
  font-weight: 500;
  letter-spacing: 0.02em;
}

.brand-version {
  color: rgba(255, 255, 255, 0.85);
  font-size: 0.7rem;
}

/* Vuetify's default 32px icon-title spacer wastes width and ellipsizes long titles;
   --v-list-group-prepend must shrink with it so section children align under the section title */
.nav-menu {
  --v-list-group-prepend: 20px;
}

.nav-menu :deep(.v-list-item__spacer) {
  width: 12px;
}

/* Rail: no room for indent; section children show a text glyph instead of a missing icon */
.nav-menu--rail :deep(.v-list-group__items .v-list-item) {
  padding-inline-start: 8px !important;
}

.glyph {
  width: 24px;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-align: center;
}

.logo-avatar :deep(.v-img) {
  width: 85%;
  height: 85%;
  flex: none;
  margin: auto;
}
</style>
