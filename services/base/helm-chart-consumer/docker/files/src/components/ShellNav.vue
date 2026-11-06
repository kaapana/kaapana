<template>
  <!-- A stand-in for the portal-ui shell, so the views can be judged in their frame. -->
  <v-navigation-drawer permanent :mobile-breakpoint="0" color="navigation" width="272">
    <div class="bg-blue py-2 mb-5">
      <div class="d-flex align-center px-2">
        <div class="d-flex align-center ga-2">
          <v-avatar color="white" :size="40">
            <v-img src="/assets/img/logo.webp" alt="Kaapana" />
          </v-avatar>
          <div class="d-flex flex-column">
            <span class="text-body-1 font-weight-medium">Kaapana</span>
            <span class="text-caption">UI mock</span>
          </div>
        </div>
        <v-spacer />
        <v-menu location="bottom start" :close-on-content-click="false">
          <template #activator="{ props: activator }">
            <v-btn v-bind="activator" icon variant="text" density="comfortable" aria-label="Notifications" class="mr-1">
              <v-badge v-if="mock.unreadCount" :content="mock.unreadCount" color="error">
                <v-icon :icon="kaapanaIcons.notificationsUnread" />
              </v-badge>
              <v-icon v-else :icon="kaapanaIcons.notifications" />
            </v-btn>
          </template>
          <v-card width="360" :elevation="5">
            <v-card-title class="d-flex align-center">
              Notifications
              <v-spacer />
              <v-btn
                v-if="mock.unreadCount"
                variant="text"
                size="small"
                @click="mock.notifications.forEach((n) => (n.read = true))"
              >
                Mark all as read
              </v-btn>
            </v-card-title>
            <v-card-text v-if="!mock.notifications.length" class="text-body-2 text-medium-emphasis">
              No notifications yet. A deployment that becomes ready shows up here.
            </v-card-text>
            <v-list v-else lines="three" density="compact">
              <v-list-item
                v-for="n in mock.notifications"
                :key="n.id"
                :title="n.title"
                :subtitle="`${n.text} · ${relative(n.at)}`"
                @click="n.read = true"
              >
                <template #prepend>
                  <v-icon
                    :icon="n.type === 'error' ? kaapanaIcons.error : n.type === 'success' ? kaapanaIcons.success : kaapanaIcons.info"
                    :color="n.read ? undefined : n.type"
                  />
                </template>
              </v-list-item>
            </v-list>
          </v-card>
        </v-menu>
        <v-menu location="bottom start">
          <template #activator="{ props: activator }">
            <v-btn v-bind="activator" icon variant="text" density="comfortable" :aria-label="`Account of ${mock.persona.name}`">
              <v-icon :icon="kaapanaIcons.account" />
            </v-btn>
          </template>
          <v-card width="280" :elevation="5">
            <v-card-text>
              <div class="text-subtitle-1">{{ mock.persona.name }}</div>
              <div class="text-body-2 text-medium-emphasis">
                {{ mock.role ? roleLabels[mock.role] : 'No role' }} in {{ mock.project?.name }}
              </div>
              <div class="text-caption text-medium-emphasis mt-2">Switch the person in the mock bar at the top.</div>
            </v-card-text>
          </v-card>
        </v-menu>
      </div>
      <div class="px-2 pt-4">
        <v-select
          :model-value="mock.projectId"
          :items="mock.accessibleProjects"
          item-title="name"
          item-value="id"
          label="Project"
          variant="outlined"
          rounded="lg"
          density="compact"
          hide-details
          class="project-select"
          @update:model-value="mock.switchProject($event)"
        />
      </div>
    </div>

    <v-list
      v-model:opened="opened"
      density="compact"
      nav
      color="primary"
      open-strategy="multiple"
    >
      <v-list-group value="workflows">
        <template #activator="{ props: activator }">
          <v-list-item v-bind="activator" prepend-icon="mdi-gamepad-variant" title="Workflows" />
        </template>
        <v-list-item
          v-for="entry in otherEntries"
          :key="entry.id"
          :to="`/other/${entry.id}`"
          :prepend-icon="entry.icon"
          :title="entry.label"
          class="text-medium-emphasis"
        />
        <v-list-item to="/applications" prepend-icon="mdi-apps-box" title="Applications" />
        <v-list-item v-if="mock.can.deploy" to="/catalog" prepend-icon="mdi-view-grid-plus-outline" title="Application Catalog" />
      </v-list-group>
      <v-list-group v-if="mock.can.manageAvailability" value="system">
        <template #activator="{ props: activator }">
          <v-list-item v-bind="activator" prepend-icon="mdi-view-dashboard-variant" title="System" />
        </template>
        <v-list-item to="/availability" prepend-icon="mdi-toggle-switch-outline" title="Application Availability" />
        <v-list-item to="/projects" prepend-icon="mdi-folder-account-outline" title="Projects" />
      </v-list-group>
    </v-list>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { kaapanaIcons } from '@kaapana/base-ui'
import { roleLabels, useMockStore } from '@/stores/mock'
import { relative } from '@/utils/format'

const mock = useMockStore()
const opened = ref<string[]>(['workflows', 'system'])

// Activating an entry may collapse the other section; the mock keeps both open so
// switching the person never hides the Applications entry.
watch(opened, (now) => {
  if (!now.includes('workflows') || !now.includes('system')) opened.value = ['workflows', 'system']
})

/** Existing shell entries, shown for context; they are not part of the mock. */
const otherEntries = [
  { id: 'data-upload', label: 'Data Upload', icon: 'mdi-cloud-upload' },
  { id: 'datasets', label: 'Datasets', icon: 'mdi-view-gallery-outline' },
  { id: 'workflow-execution', label: 'Workflow Execution', icon: 'mdi-play' },
  { id: 'workflow-results', label: 'Workflow Results', icon: 'mdi-chart-bar-stacked' },
]
</script>

<style scoped>
.project-select :deep(.v-field) {
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-on-surface));
}
</style>
