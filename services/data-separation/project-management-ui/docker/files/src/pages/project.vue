<template>
  <v-snackbar v-model="isSnackbarVisible" :timeout="3000" location="top" :color="snackbarColor" elevation="2" closable>
    {{ snackbarMessage }}
  </v-snackbar>

  <v-container fluid class="pm-view">
    <div class="d-flex justify-space-between mb-2">
      <v-btn variant="text" prepend-icon="mdi-arrow-left" @click="goToProjectsList">
        Projects
      </v-btn>
      <v-btn variant="text" prepend-icon="mdi-refresh" @click="refresh">Refresh</v-btn>
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
          <v-skeleton-loader v-else :loading="!project" type="heading" width="200" />
          <div v-if="userHasAdminAccess && project?.name !== 'admin'" class="d-flex ga-1">
            <v-btn
              icon="mdi-pencil"
              size="default"
              variant="text"
              color="primary"
              @click="openEditDialog"
            />
            <v-btn
              v-if="!project?.is_archived"
              icon="mdi-archive-arrow-down"
              size="default"
              variant="text"
              color="primary"
              @click="archiveDialog = true"
            />
            <v-btn
              v-if="project?.is_archived"
              icon="mdi-archive-arrow-up"
              size="default"
              variant="text"
              color="primary"
              @click="unarchiveProject"
            />
            <v-btn
              icon="mdi-trash-can"
              size="default"
              variant="text"
              color="error"
              @click="openDeleteDialog"
            />
          </div>
        </div>
        <v-alert v-if="project?.is_archived" type="warning" density="compact" variant="tonal" class="mb-3">
          This project is archived and read-only. Unarchive it to make changes.
        </v-alert>
        <p v-if="project?.description" class="text-body-1 text-medium-emphasis">
          {{ project.description }}
        </p>
      </v-col>
    </v-row>

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

    <template v-if="userHasAdminAccess || can(project?.id, 'view_applications')">
      <v-divider class="my-4" />

      <!-- ── Multiinstallable Applications ────────────────────────── -->
      <v-row>
        <MultiinstallableApplications :key="`apps-${refreshKey}`" :project="project" :expanded="isAppsSectionExpanded"
          @toggle="isAppsSectionExpanded = $event" />
      </v-row>
    </template>

    <template v-if="userHasAdminAccess || can(project?.id, 'view_active_apps')">
      <v-divider class="my-4" />

      <!-- ── Active Project Applications ──────────────────────────── -->
      <v-row>
        <ActiveProjectApplications :key="`active-${refreshKey}`" :project="project" :expanded="isActiveAppsSectionExpanded"
          @toggle="isActiveAppsSectionExpanded = $event" @confirm-uninstall="confirmAppUninstall" />
      </v-row>
    </template>

    <v-divider class="my-4" />

    <!-- ── Dialogs ───────────────────────────────────────────────── -->
    <v-dialog v-model="deleteDialog" max-width="500">
      <DeleteProjectDialog v-if="project" :project="project"
        @confirm="handleDeleteConfirm" @cancel="deleteDialog = false" />
    </v-dialog>

    <v-dialog v-model="editDialog" max-width="600">
      <EditProjectDialog v-if="project" :project="project"
        @success="handleEditSuccess" @cancel="editDialog = false" @error="handleEditError" />
    </v-dialog>

    <v-dialog v-model="archiveDialog" max-width="560">
      <ArchiveProjectDialog v-if="project" :project="project"
        @confirm="confirmArchive" @cancel="archiveDialog = false" />
    </v-dialog>

  </v-container>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { aiiApiGet, aiiApiPost, aiiApiDelete, kubeHelmPost, setScopedProject } from '@/common/services';
import { ProjectItem } from '@/common/types';
import ProjectUsers from '@/components/ProjectUsers.vue';
import ProjectWorkflows from '@/components/ProjectWorkflows.vue';
import MultiinstallableApplications from '@/components/MultiinstallableApplications.vue';
import ActiveProjectApplications from '@/components/ActiveProjectApplications.vue';
import DeleteProjectDialog from '@/components/DeleteProjectDialog.vue';
import EditProjectDialog from '@/components/EditProjectDialog.vue';
import ArchiveProjectDialog from '@/components/ArchiveProjectDialog.vue';
import { usePermissions } from '@/permissions/usePermissions';
import { usePermissionsStore } from '@/permissions/permissions.store';
import { isAdminUser, waitForStoreUser } from '@/common/userAccess';

export default defineComponent({
  components: {
    ProjectUsers,
    ProjectWorkflows,
    MultiinstallableApplications,
    ActiveProjectApplications,
    DeleteProjectDialog,
    EditProjectDialog,
    ArchiveProjectDialog,
  },

  setup() {
    const { can } = usePermissions();
    return { can };
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

      deleteDialog: false,
      editDialog: false,
      archiveDialog: false,

      isSnackbarVisible: false,
      snackbarMessage: '',
      snackbarColor: 'info',
    };
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
    notify(message: string, color = 'info'): void {
      this.snackbarMessage = message;
      this.snackbarColor = color;
      this.isSnackbarVisible = true;
    },

    goToProjectsList(): void {
      this.$router.push('/');
    },

    async refresh(): Promise<void> {
      await this.loadProject({ silent: true });
      this.refreshKey++;
    },

    async loadProject({ silent = false } = {}): Promise<void> {
      if (!this.projectId) return;
      try {
        const project: ProjectItem = await aiiApiGet(`projects/${this.projectId}`);
        this.project = project;
        setScopedProject(project);
        if (!silent) {
          this.notify(`Selected project: ${project.name}.`, 'success');
        }
        usePermissionsStore().loadProjectWhitelist(this.projectId);
      } catch (error) {
        console.error('Failed to load project:', error);
      }
    },

    async confirmAppUninstall(app: any): Promise<void> {
      try {
        await kubeHelmPost('helm-delete-chart', { release_name: app.release_name });
        this.notify(`Application "${app.release_name}" uninstalled successfully.`, 'success');
        await this.refresh();
      } catch (error: any) {
        console.error('Failed to uninstall application:', error);
        const detail = error?.response?.data?.detail ?? error?.message ?? 'Unknown error';
        this.notify(`Failed to uninstall "${app.release_name}": ${detail}`, 'error');
      }
    },

    openEditDialog(): void { this.editDialog = true; },

    async handleEditSuccess(): Promise<void> {
      this.editDialog = false;
      await this.loadProject();
      this.notify('Project updated successfully.', 'success');
    },

    handleEditError(msg: string): void { this.notify(msg, 'error'); },

    openDeleteDialog(): void { this.deleteDialog = true; },

    async handleDeleteConfirm(): Promise<void> {
      this.deleteDialog = false;
      try {
        await aiiApiDelete(`projects/${this.projectId}`);
        this.$router.push('/');
      } catch (error) {
        console.error(error);
        this.notify('Failed to delete project.', 'error');
      }
    },

    async confirmArchive(): Promise<void> {
      this.archiveDialog = false;
      try {
        await aiiApiPost(`projects/${this.projectId}/archive`, {});
        await this.loadProject();
        this.notify(`Project "${this.project?.name}" archived.`, 'success');
      } catch (error) {
        console.error(error);
        this.notify('Failed to archive project.', 'error');
      }
    },

    async unarchiveProject(): Promise<void> {
      try {
        await aiiApiPost(`projects/${this.projectId}/unarchive`, {});
        await this.loadProject();
        this.notify(`Project "${this.project?.name}" unarchived.`, 'success');
      } catch (error) {
        console.error(error);
        this.notify('Failed to unarchive project.', 'error');
      }
    },

  },
});
</script>
