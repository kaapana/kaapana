<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon class="mr-2">mdi-view-grid-outline</v-icon>
      Capabilities
    </v-card-title>
    <v-card-text>
      <div class="step-grid">
        <v-card
          v-for="step in steps"
          :key="step.title"
          class="workflow-step text-center"
          variant="tonal"
          :disabled="!step.allowed"
          v-bind="step.allowed ? { onClick: () => navigateShell(step.shellRoute) } : {}"
        >
          <v-card-text>
            <v-icon size="x-large" color="primary">{{ step.icon }}</v-icon>
            <div class="text-subtitle-2 mt-2">
              {{ step.title }}
              <v-badge v-if="step.badge > 0" :content="step.badge" color="primary" inline />
            </div>
            <div class="text-caption text-medium-emphasis">{{ step.description }}</div>
          </v-card-text>
        </v-card>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { checkAuthR } from '@/utils/utils'
import { navigateShell, useAuthStore } from '@kaapana/base-ui'
import { useCommonDataStore } from '@/stores/commonData'
import { fetchBadgeCount } from '@/api/badges'

const authStore = useAuthStore()
const commonDataStore = useCommonDataStore()

interface Step {
  title: string
  icon: string
  description: string
  shellRoute: string
  policyPath: string
  // Only Tasks carries a count today; a generic per-card badge map would be
  // speculative until a second view declares kaapana.ai/ui.badge-path.
  badged?: boolean
}

// Count endpoint the Tasks ingress declares (see app-ui-chart/service.yaml).
const TASKS_BADGE_PATH = '/kube-helm-api/pending-applications-count'

// The platform's capabilities, one card each. OPA-denied entries stay visible
// but dimmed — the list is explanatory, not just navigation.
const workflowSteps: Step[] = [
  { title: 'Data Upload', icon: 'mdi-cloud-upload', description: 'Bring DICOM or NIfTI data onto the platform', shellRoute: '/web/workflows/data-upload', policyPath: '/data-upload-ui/' },
  { title: 'Datasets', icon: 'mdi-view-gallery-outline', description: 'Curate and explore your data', shellRoute: '/web/workflows/datasets', policyPath: '/data-gallery-ui/' },
  { title: 'Workflow Execution', icon: 'mdi-play', description: 'Run processing workflows on a dataset', shellRoute: '/web/workflows/workflow-execution', policyPath: '/workflow-execution-ui/' },
  { title: 'Workflow List', icon: 'mdi-clipboard-text-outline', description: 'Monitor running and past workflows', shellRoute: '/web/workflows/workflows', policyPath: '/workflow-list-ui/' },
  { title: 'Results', icon: 'mdi-chart-bar-stacked', description: 'Browse the results of your workflows', shellRoute: '/web/workflows/results-browser', policyPath: '/results-ui/' },
  { title: 'Tasks', icon: 'mdi-checkbox-multiple-marked', description: 'Handle workflow tasks waiting for your input', shellRoute: '/web/workflows/tasks', policyPath: '/app-ui/', badged: true },
  { title: 'Apps', icon: 'mdi-apps-box', description: 'Open the applications running in this project', shellRoute: '/web/workflows/apps', policyPath: '/app-ui/' },
  { title: 'Extensions', icon: 'mdi-puzzle', description: 'Install more workflows and apps', shellRoute: '/web/-/extensions', policyPath: '/extensions-ui/' },
]

// Same cadence the shell polls its menu badges at.
const BADGE_POLL_INTERVAL_MS = 15_000

const pendingTasks = ref(0)
let badgeTimer: ReturnType<typeof setInterval> | null = null

// Like the shell's menu badges: a failed poll keeps the last known count
// instead of blanking the card.
async function refreshTasksBadge() {
  const count = await fetchBadgeCount(TASKS_BADGE_PATH)
  if (count !== null) pendingTasks.value = count
}

onMounted(() => {
  refreshTasksBadge()
  badgeTimer = setInterval(refreshTasksBadge, BADGE_POLL_INTERVAL_MS)
})

onUnmounted(() => {
  if (badgeTimer) clearInterval(badgeTimer)
})

const steps = computed(() =>
  workflowSteps.map((step) => ({
    ...step,
    allowed: checkAuthR(commonDataStore.policyData, step.policyPath, authStore.currentUser),
    badge: step.badged ? pendingTasks.value : 0,
  })),
)
</script>

<style scoped>
.step-grid {
  display: grid;
  /* min() keeps the track from outgrowing a very narrow card and forcing the
     page to scroll sideways. */
  grid-template-columns: repeat(auto-fit, minmax(min(140px, 100%), 1fr));
  gap: 8px;
}
</style>
