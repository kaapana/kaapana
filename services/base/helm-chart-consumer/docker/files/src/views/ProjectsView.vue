<template>
  <UnavailableState v-if="!mock.can.manageProjects" view="Projects" />
  <v-container v-else class="text-left">
    <h1 class="text-h4">Projects <StoryRef ids="12.2" /></h1>
    <p class="text-body-2 text-medium-emphasis mt-1 mb-4">
      A stand-in for the project management view, reduced to deleting a project.
    </p>

    <v-card :elevation="2">
      <v-data-table
        :headers="headers"
        :items="mock.projects"
        item-value="id"
        :items-per-page="-1"
        hide-default-footer
      >
        <template #item.name="{ item }">
          <div class="py-2">
            <div class="font-weight-medium">{{ item.name }}</div>
            <div class="text-caption text-medium-emphasis">{{ item.id }}</div>
          </div>
        </template>
        <template #item.members="{ item }">{{ Object.keys(item.members).length }}</template>
        <template #item.apps="{ item }">
          <span v-if="!appsOf(item.id).length" class="text-medium-emphasis">None</span>
          <span v-else>{{
            appsOf(item.id)
              .map((d) => d.name)
              .join(', ')
          }}</span>
        </template>
        <template #item.actions="{ item }">
          <v-btn
            :icon="kaapanaIcons.delete"
            variant="text"
            color="error"
            size="small"
            :aria-label="`Delete project ${item.name}`"
            @click="ask(item)"
          />
        </template>
        <template #no-data>
          <v-empty-state
            size="56"
            title="No projects"
            text="All projects were deleted. Reset the mock data to start over."
          />
        </template>
      </v-data-table>
    </v-card>

    <!-- Q9, answer "undeploy": a destructive confirmation that names what goes with the project. -->
    <ConfirmDialog
      :model-value="open && !refused"
      :title="`Delete project “${target?.name ?? ''}”?`"
      :text="confirmText"
      confirm-text="Delete project"
      color="error"
      @update:model-value="open = $event"
      @confirm="target && mock.deleteProject(target.id)"
    />

    <!-- Q9, answer "refuse": nothing to confirm, only what to do first. -->
    <v-dialog :model-value="open && refused" max-width="400" @update:model-value="open = $event">
      <v-card v-if="target" :elevation="5">
        <v-card-title class="text-wrap"
          >“{{ target.name }}” still has deployed applications</v-card-title
        >
        <v-card-text>
          Undeploy
          {{
            appsOf(target.id)
              .map((d) => d.name)
              .join(', ')
          }}
          first, then delete the project.
          <StoryRef ids="Q9" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn autofocus @click="open = false">Close</v-btn>
          <v-btn color="primary" @click="showApplications">Show applications</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ConfirmDialog, kaapanaIcons } from '@kaapana/base-ui'
import StoryRef from '@/components/StoryRef.vue'
import UnavailableState from '@/components/UnavailableState.vue'
import type { Project } from '@/mock/types'
import { useMockStore } from '@/stores/mock'

const mock = useMockStore()
const router = useRouter()
// The target outlives the open flag so a dialog keeps its content while it fades out.
const target = ref<Project | null>(null)
const open = ref(false)

function ask(project: Project) {
  target.value = project
  open.value = true
}

const headers = [
  { title: 'Project', key: 'name' },
  { title: 'Members', key: 'members', sortable: false },
  { title: 'Deployed applications', key: 'apps', sortable: false },
  { title: '', key: 'actions', sortable: false, align: 'end' as const },
]

function appsOf(projectId: string) {
  return mock.deployed.filter((d) => d.projectId === projectId)
}

const refused = computed(
  () =>
    !!target.value &&
    mock.options.projectDeletion === 'refuse' &&
    appsOf(target.value.id).length > 0,
)

const confirmText = computed(() => {
  if (!target.value) return ''
  const apps = appsOf(target.value.id)
  const data = 'The project bucket and its data are deleted with the project.'
  if (!apps.length) return data
  const names = apps.map((d) => d.name).join(', ')
  return `This also undeploys ${apps.length === 1 ? 'its application' : `its ${apps.length} applications`} (${names}) and deletes their workspace volumes. ${data}`
})

function showApplications() {
  const id = target.value?.id
  open.value = false
  if (id) mock.projectId = id
  router.push('/applications')
}
</script>
