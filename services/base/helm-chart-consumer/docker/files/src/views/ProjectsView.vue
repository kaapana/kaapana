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
          <span v-if="!mock.projectAppsOf(item.id).length" class="text-medium-emphasis">None</span>
          <span v-else>{{
            mock
              .projectAppsOf(item.id)
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

    <ConfirmDialog
      v-model="open"
      :title="`Delete project “${target?.name ?? ''}”?`"
      text="The project bucket and its data are deleted with the project."
      confirm-text="Delete project"
      color="error"
      @confirm="remove"
    />

    <v-dialog v-model="refusalOpen" max-width="400">
      <v-card v-if="target" :elevation="5">
        <v-card-title class="text-wrap"
          >“{{ target.name }}” still has deployed applications</v-card-title
        >
        <v-card-text>
          Undeploy {{ blocking.map((d) => d.name).join(', ') }} first, then delete the project.
          Platform-wide applications do not block the deletion.
          <StoryRef ids="12.2 Q9" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn autofocus @click="refusalOpen = false">Close</v-btn>
          <v-btn color="primary" @click="showApplications">Show applications</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ConfirmDialog, kaapanaIcons } from '@kaapana/base-ui'
import StoryRef from '@/components/StoryRef.vue'
import UnavailableState from '@/components/UnavailableState.vue'
import type { DeployedApp, Project } from '@/mock/types'
import { useMockStore } from '@/stores/mock'

const mock = useMockStore()
const router = useRouter()
// The target outlives the open flag so a dialog keeps its content while it fades out.
const target = ref<Project | null>(null)
const open = ref(false)
const blocking = ref<DeployedApp[]>([])
const refusalOpen = ref(false)

function ask(project: Project) {
  target.value = project
  blocking.value = mock.projectAppsOf(project.id)
  if (blocking.value.length > 0) refusalOpen.value = true
  else open.value = true
}

function remove() {
  if (!target.value) return
  blocking.value = mock.deleteProject(target.value.id)
  refusalOpen.value = blocking.value.length > 0
}

const headers = [
  { title: 'Project', key: 'name' },
  { title: 'Members', key: 'members', sortable: false },
  { title: 'Deployed applications', key: 'apps', sortable: false },
  { title: '', key: 'actions', sortable: false, align: 'end' as const },
]

function showApplications() {
  const id = target.value?.id
  refusalOpen.value = false
  if (id) mock.projectId = id
  router.push('/applications')
}
</script>
