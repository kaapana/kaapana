<template>
  <v-container fluid class="pm-view">
    <div class="d-flex justify-space-between mb-2">
      <v-btn variant="text" :prepend-icon="projectIcons.back" @click="goToProjectsList">
        Projects
      </v-btn>
      <v-btn variant="text" :prepend-icon="kaapanaIcons.refresh" @click="refresh">Refresh</v-btn>
    </div>

    <v-row>
      <v-col>
        <div class="d-flex align-start justify-space-between mb-3">
          <div v-if="project">
            <div class="d-flex align-center ga-2">
              <h1 class="text-h4">{{ project.name }}</h1>
              <v-chip v-if="project.is_archived" color="warning" size="small">Archived</v-chip>
            </div>
            <div v-if="project.external_id" class="text-caption text-medium-emphasis">
              {{ project.external_id }}
            </div>
          </div>
          <v-skeleton-loader v-else-if="!loadError" type="heading" width="200" />
          <div v-if="userHasAdminAccess && project?.name !== 'admin'" class="d-flex ga-1">
            <v-tooltip v-if="!project?.is_archived" text="Edit project" location="top">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  :icon="kaapanaIcons.edit"
                  aria-label="Edit project"
                  :disabled="busy !== null"
                  size="default"
                  variant="text"
                  color="primary"
                  @click="openEditDialog"
                />
              </template>
            </v-tooltip>
            <v-tooltip v-if="!project?.is_archived" text="Archive project" location="top">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  :icon="projectIcons.archive"
                  aria-label="Archive project"
                  :loading="busy === 'archive'"
                  :disabled="busy !== null"
                  size="default"
                  variant="text"
                  color="primary"
                  @click="openArchiveDialog"
                />
              </template>
            </v-tooltip>
            <v-tooltip v-if="project?.is_archived" text="Unarchive project" location="top">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  :icon="projectIcons.unarchive"
                  aria-label="Unarchive project"
                  :loading="busy === 'unarchive'"
                  :disabled="busy !== null"
                  size="default"
                  variant="text"
                  color="primary"
                  @click="unarchiveProject"
                />
              </template>
            </v-tooltip>
            <v-tooltip text="Delete project" location="top">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  :icon="kaapanaIcons.delete"
                  aria-label="Delete project"
                  :loading="busy === 'delete'"
                  :disabled="busy !== null"
                  size="default"
                  variant="text"
                  color="error"
                  @click="openDeleteDialog"
                />
              </template>
            </v-tooltip>
          </div>
        </div>
        <FailureAlert
          v-if="loadError"
          title="Project not loaded"
          text="Could not load this project."
          :error="loadError"
          :retry="loadProject"
        />
        <v-alert
          v-if="project?.is_archived"
          type="warning"
          density="compact"
          variant="tonal"
          class="mb-3"
        >
          This project is archived: its details, members and allowed workflows cannot be changed.
          Unarchive it to make changes.
        </v-alert>
        <p v-if="project?.description" class="text-body-1 text-medium-emphasis">
          {{ project.description }}
        </p>
      </v-col>
    </v-row>

    <template v-if="project">
      <!-- ── Project Users ────────────────────────────────────────── -->
      <v-row>
        <ProjectUsers :key="`users-${refreshKey}`" :project="project" :expanded="isUsersSectionExpanded" @toggle="isUsersSectionExpanded = $event" />
      </v-row>

      <v-divider class="my-4" />

      <!-- ── Executable Workflows ─────────────────────────────────── -->
      <v-row>
        <ProjectWorkflows :key="`workflows-${refreshKey}`" :project="project" :expanded="isWorkflowsSectionExpanded"
          @toggle="isWorkflowsSectionExpanded = $event" />
      </v-row>

      <template v-if="can(project?.id, 'view_applications')">
        <v-divider class="my-4" />

        <!-- ── Multiinstallable Applications ────────────────────────── -->
        <v-row>
          <MultiinstallableApplications
            :key="`apps-${refreshKey}`"
            :project="project"
            :expanded="isAppsSectionExpanded"
            @toggle="isAppsSectionExpanded = $event"
            @launched="activeAppsKey++"
          />
        </v-row>
      </template>

      <template v-if="can(project?.id, 'view_active_apps')">
        <v-divider class="my-4" />

        <!-- ── Active Project Applications ──────────────────────────── -->
        <v-row>
          <ActiveProjectApplications
            :key="`active-${refreshKey}-${activeAppsKey}`"
            :project="project"
            :expanded="isActiveAppsSectionExpanded"
            @toggle="isActiveAppsSectionExpanded = $event"
            :busy-release="uninstallingRelease"
            @confirm-uninstall="confirmAppUninstall"
          />
        </v-row>
      </template>

      <v-divider class="my-4" />
    </template>

    <!-- ── Dialogs ───────────────────────────────────────────────── -->
    <GuardedDialog
      v-slot="{ requestClose }"
      v-model="editDialog"
      :dirty="editDirty"
      max-width="600"
    >
      <EditProjectDialog
        v-if="editDialog && project"
        :project="project"
        @success="handleEditSuccess"
        @cancel="requestClose"
        @update:dirty="editDirty = $event"
      />
    </GuardedDialog>

    <ConfirmDialog
      v-model="confirmOpen"
      :color="confirmation.color"
      :title="confirmation.title"
      :text="confirmation.text"
      :confirm-text="confirmation.confirmText"
      @confirm="runConfirmed"
    />
  </v-container>
</template>

<script lang="ts">
import { kaapanaIcons, projectIcons } from '@/utils/projectIcons'
import { defineComponent } from 'vue'
import {
  aiiApiGet,
  aiiApiPost,
  aiiApiDelete,
  kubeHelmPost,
  setScopedProject,
} from '@/common/services'
import { ProjectItem } from '@/common/types'
import ProjectUsers from '@/components/ProjectUsers.vue'
import ProjectWorkflows from '@/components/ProjectWorkflows.vue'
import MultiinstallableApplications from '@/components/MultiinstallableApplications.vue'
import ActiveProjectApplications from '@/components/ActiveProjectApplications.vue'
import EditProjectDialog from '@/components/EditProjectDialog.vue'
import FailureAlert from '@/components/FailureAlert.vue'
import GuardedDialog from '@/components/GuardedDialog.vue'
import { ConfirmDialog, refreshShell } from '@kaapana/base-ui'
import { notify } from '@kyvg/vue3-notification'
import { notifyFailure } from '@/utils/notifyFailure'
import { useConfirmation } from '@/composables/useConfirmation'
import { confirmDiscard } from '@/composables/useDiscardConfirmation'
import { archiveProjectConfirmation, deleteProjectConfirmation } from '@/utils/projectConfirmations'
import { usePermissions } from '@/permissions/usePermissions'
import { usePermissionsStore } from '@/permissions/permissions.store'
import { isAdminUser, waitForStoreUser } from '@/common/userAccess'

export default defineComponent({
  components: {
    ProjectUsers,
    ProjectWorkflows,
    MultiinstallableApplications,
    ActiveProjectApplications,
    EditProjectDialog,
    FailureAlert,
    ConfirmDialog,
    GuardedDialog,
  },

  setup() {
    const { can } = usePermissions()
    const { confirmOpen, confirmation, ask, runConfirmed } = useConfirmation()
    return { kaapanaIcons, projectIcons, can, confirmOpen, confirmation, ask, runConfirmed }
  },

  data() {
    return {
      // @ts-ignore
      projectId: this.$route.params.id as string,
      project: null as ProjectItem | null,
      userHasAdminAccess: false,

      isUsersSectionExpanded: false,
      isWorkflowsSectionExpanded: false,
      isAppsSectionExpanded: false,
      isActiveAppsSectionExpanded: false,

      refreshKey: 0,
      activeAppsKey: 0,
      loadError: null as unknown,

      busy: null as 'delete' | 'archive' | 'unarchive' | null,
      uninstallingRelease: null as string | null,

      editDialog: false,
      editDirty: false,
    }
  },

  mounted() {
    this.loadProject();
    waitForStoreUser((user) => {
      this.userHasAdminAccess = isAdminUser(user);
    });
  },

  unmounted() {
    setScopedProject(null);
  },

  watch: {
    '$route.params.id'(newId: string) {
      this.projectId = newId;
      this.loadProject();
    },
  },

  methods: {
    goToProjectsList(): void {
      this.$router.push('/');
    },

    async refresh(): Promise<void> {
      // Remounting the sections drops their staged changes.
      if (!(await confirmDiscard())) return
      await this.loadProject()
      this.refreshKey++
    },

    async loadProject(): Promise<void> {
      if (!this.projectId) return
      this.loadError = null
      try {
        const project: ProjectItem = await aiiApiGet(`projects/${this.projectId}`)
        this.project = project
        setScopedProject(project)
        // Only narrows which application actions are offered; kube-helm checks the
        // whitelist itself, and the application section reports its own load failure.
        usePermissionsStore()
          .loadProjectWhitelist(this.projectId)
          .catch(() => undefined)
      } catch (error) {
        this.loadError = error
      }
    },

    async confirmAppUninstall(app: any): Promise<void> {
      this.uninstallingRelease = app.release_name
      try {
        await kubeHelmPost('helm-delete-chart', { release_name: app.release_name })
        notify({
          type: 'success',
          text: `${app.annotations['kaapana.ai/display-name']} is being removed.`,
        })
        this.activeAppsKey++
      } catch (error: unknown) {
        notifyFailure(
          'Application not uninstalled',
          `Could not uninstall ${app.annotations['kaapana.ai/display-name']}.`,
          error,
        )
      } finally {
        this.uninstallingRelease = null
      }
    },

    openEditDialog(): void { this.editDialog = true; },

    async handleEditSuccess(): Promise<void> {
      this.editDialog = false
      refreshShell()
      await this.loadProject()
      notify({ type: 'success', text: 'Project updated.' })
    },

    openDeleteDialog(): void {
      if (!this.project) return
      this.ask(deleteProjectConfirmation(this.project, () => this.deleteProject()))
    },

    async deleteProject(): Promise<void> {
      this.busy = 'delete'
      try {
        await aiiApiDelete(`projects/${this.projectId}`)
        refreshShell()
        this.$router.push('/')
        notify({ type: 'success', text: `Project "${this.project?.name}" deleted.` })
      } catch (error) {
        notifyFailure('Project not deleted', `Could not delete "${this.project?.name}".`, error)
      } finally {
        this.busy = null
      }
    },

    openArchiveDialog(): void {
      if (!this.project) return
      this.ask(archiveProjectConfirmation(this.project, () => this.archiveProject()))
    },

    async archiveProject(): Promise<void> {
      this.busy = 'archive'
      try {
        await aiiApiPost(`projects/${this.projectId}/archive`, {})
        refreshShell()
        await this.loadProject()
        notify({ type: 'success', text: `Project "${this.project?.name}" archived.` })
      } catch (error) {
        notifyFailure('Project not archived', `Could not archive "${this.project?.name}".`, error)
      } finally {
        this.busy = null
      }
    },

    async unarchiveProject(): Promise<void> {
      this.busy = 'unarchive'
      try {
        await aiiApiPost(`projects/${this.projectId}/unarchive`, {})
        refreshShell()
        await this.loadProject()
        notify({ type: 'success', text: `Project "${this.project?.name}" unarchived.` })
      } catch (error) {
        notifyFailure(
          'Project not unarchived',
          `Could not unarchive "${this.project?.name}".`,
          error,
        )
      } finally {
        this.busy = null
      }
    },

  },
});
</script>
