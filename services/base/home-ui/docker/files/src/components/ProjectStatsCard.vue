<template>
  <v-card class="data-card">
    <v-card-title class="d-flex align-center">
      <v-icon class="mr-2">mdi-database-outline</v-icon>
      Data
    </v-card-title>
    <v-card-text>
      <div v-if="totalsUnavailable" class="text-medium-emphasis">
        Platform totals not available
      </div>
      <!-- The labels here double as the legend for the icons repeated in the
           project rows below, which have no room for words. -->
      <v-row v-else dense class="text-center">
        <v-col v-for="stat in stats" :key="stat.label" cols="4">
          <div class="stat-value text-h5">{{ totals[stat.label] ?? '—' }}</div>
          <div class="text-caption text-medium-emphasis">
            <v-icon size="x-small" class="mr-1">{{ stat.icon }}</v-icon>
            {{ stat.label }}
          </div>
        </v-col>
      </v-row>

      <template v-if="projectStore.availableProjects.length">
        <v-divider class="my-3" />
        <div class="text-body-2 mb-1">Your projects</div>
        <div class="project-scroll">
          <v-list density="compact" class="pa-0">
            <v-list-item
              v-for="project in projectStore.availableProjects"
              :key="project.id"
              lines="two"
              color="primary"
              :active="isSelected(project)"
              @click="onSelect(project)"
            >
              <template #prepend>
                <v-icon size="small">
                  {{ isSelected(project) ? 'mdi-folder-open-outline' : 'mdi-folder-outline' }}
                </v-icon>
              </template>
              <!-- The name is the only part allowed to truncate: a clipped
                   count would read as a wrong number. -->
              <div class="d-flex align-center">
                <v-list-item-title>{{ project.name }}</v-list-item-title>
                <v-chip v-if="project.role_name" size="x-small" variant="tonal" class="role-chip ml-2">
                  {{ project.role_name }}
                </v-chip>
              </div>
              <div
                v-if="projectStats[String(project.id)]"
                class="project-meta d-flex align-center text-caption text-medium-emphasis"
              >
                <span v-for="stat in stats" :key="stat.label" class="stat-group" :title="stat.label">
                  <v-icon size="x-small">{{ stat.icon }}</v-icon>
                  {{ projectStats[String(project.id)]![stat.label] ?? '—' }}
                </span>
              </div>
              <template #append>
                <!-- The dialog reads the document's project, so it belongs to
                     the row that names it; the others are switch targets. -->
                <v-btn
                  v-if="isSelected(project)"
                  icon="mdi-chart-bar"
                  size="x-small"
                  variant="text"
                  aria-label="Details"
                  @click.stop="detailOpen = true"
                />
                <v-icon v-else size="small">mdi-arrow-right</v-icon>
              </template>
            </v-list-item>
          </v-list>
        </div>
      </template>
    </v-card-text>

    <ProjectDetailDialog v-model="detailOpen" />
  </v-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import ProjectDetailDialog from '@/components/ProjectDetailDialog.vue'
import { switchProject, useProjectStore, type Project } from '@kaapana/base-ui'
import { loadProjectDashboard } from '@/api/dashboard'
import { fetchMetric } from '@/api/monitoring'

const projectStore = useProjectStore()

const stats = [
  { label: 'Patients', gauge: 'dicom_patients_total', icon: 'mdi-account-multiple-outline' },
  { label: 'Studies', gauge: 'dicom_studies_total', icon: 'mdi-folder-multiple-outline' },
  { label: 'Series', gauge: 'dicom_series_total', icon: 'mdi-image-multiple-outline' },
]

const totals = ref<Record<string, number | null>>({ Patients: null, Studies: null, Series: null })
const totalsLoaded = ref(false)
const projectStats = ref<Record<string, Record<string, number | string> | null>>({})
const detailOpen = ref(false)

const totalsUnavailable = computed(
  () => totalsLoaded.value && stats.every((stat) => totals.value[stat.label] === null),
)

function isSelected(project: Project) {
  return project.id == projectStore.selectedProject.id
}

function slugOf(project: Project) {
  return String(project.short_id ?? project.id)
}

// Ask the shell to switch rather than navigating the top window ourselves, so
// its view-dirty confirm still runs and the shell is not reloaded; it swaps the
// prefix and keeps the route, like its own project selector.
function onSelect(project: Project) {
  if (isSelected(project)) {
    detailOpen.value = true
    return
  }
  switchProject(slugOf(project))
}

// kaapana-backend's get_dashboard makes BLOCKING OpenSearch calls inside an
// async def, so each in-flight request occupies a whole uvicorn worker (4
// total) — more than 2 would starve the view's own monitoring polls behind it.
const STATS_CONCURRENCY = 2

async function loadProjectStats(projects: Project[]) {
  // Archived projects are not switch targets; nobody needs their counts.
  const queue = projects.filter((p) => !p.is_archived)
  const worker = async () => {
    while (queue.length) {
      const project = queue.shift()!
      try {
        const data = await loadProjectDashboard(slugOf(project))
        projectStats.value[String(project.id)] = data.metrics ?? {}
      } catch {
        // That project shows no numbers; the rest of the list is unaffected.
        projectStats.value[String(project.id)] = null
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(STATS_CONCURRENCY, queue.length) }, worker))
}

// Keyed on the project identities, not the array reference, so re-assigning an
// identical availableProjects list does not re-run the fan-out. Component-local,
// not a cache: a remount (App.vue's :key) re-fans through { immediate: true }.
watch(
  () => projectStore.availableProjects.map((p) => slugOf(p)).join(','),
  () => {
    const projects = projectStore.availableProjects
    if (projects.length) loadProjectStats(projects)
  },
  { immediate: true },
)

onMounted(async () => {
  // Platform-wide totals come from the DICOM gauges kaapana-backend exposes to
  // Prometheus; the dashboard endpoint only ever sees one project.
  await Promise.all(
    stats.map((stat) =>
      fetchMetric(stat.gauge, `${stat.gauge}{modality="total"}`)
        // A one-off total has nothing to retry into, so a failed request reads
        // the same as an absent gauge; without this the whole card stays blank.
        .catch(() => null)
        .then((value) => {
          totals.value[stat.label] = value === null ? null : Math.round(value)
        }),
    ),
  )
  totalsLoaded.value = true
})
</script>

<style scoped>
/* A third-width column cannot hold an unbounded count, and the row must not
   widen the page when it cannot. */
.stat-value {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-scroll {
  max-height: 320px;
  overflow-y: auto;
}

.role-chip {
  flex: 0 0 auto;
}

.project-meta {
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  gap: 10px;
}

.stat-group {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}
</style>
