<template>
  <v-snackbar v-model="isSnackbarVisible" :timeout="3000" location="top" :color="snackbarColor" elevation="2" closable>
    {{ snackbarMessage }}
  </v-snackbar>

  <v-container max-width="1200" class="bg-surface rounded-lg mt-2">

    <!-- ── Back navigation ──────────────────────────────────────── -->
    <v-row no-gutters class="mb-2" justify="space-between">
      <v-col cols="auto">
        <v-btn size="x-small" variant="outlined" prepend-icon="mdi-arrow-left" @click="goToProjectsList">
          Projects
        </v-btn>
      </v-col>
      <v-col cols="auto">
        <v-btn size="x-small" variant="outlined" prepend-icon="mdi-refresh" @click="refresh">
          Refresh
        </v-btn>
      </v-col>
    </v-row>

    <!-- ── Project header card ──────────────────────────────────── -->
    <v-row>
      <v-col>
        <v-sheet class="pa-4 rounded-lg" border>
          <div class="d-flex align-center justify-space-between mb-3">
            <div v-if="project" class="d-flex align-center ga-3">
              <v-icon icon="mdi-folder-multiple" color="primary" size="large" />
              <div>
                <div class="d-flex align-center ga-2">
                  <span class="text-h5 font-weight-bold" style="font-family: monospace">{{ project.name }}</span>
                  <v-chip v-if="project.is_archived" color="warning" size="small">Archived</v-chip>
                </div>
                <div v-if="project.external_id" class="text-caption text-medium-emphasis" style="font-family: monospace">
                  {{ project.external_id }}
                </div>
              </div>
            </div>
            <v-skeleton-loader v-else :loading="!project" type="heading" width="200" />
            <div v-if="userHasAdminAccess && project?.name !== 'admin'" class="d-flex ga-1">
              <v-btn icon="mdi-pencil" size="default" variant="text" @click="openEditDialog" />
              <v-btn v-if="!project?.is_archived" icon="mdi-archive-arrow-down" size="default" variant="text" color="warning" @click="archiveDialog = true" />
              <v-btn v-if="project?.is_archived" icon="mdi-archive-arrow-up" size="default" variant="text" color="success" @click="unarchiveProject" />
              <v-btn icon="mdi-trash-can" size="default" variant="text" color="error" @click="openDeleteDialog" />
            </div>
          </div>
          <v-alert v-if="project?.is_archived" type="warning" density="compact" variant="tonal" class="mb-3">
            This project is archived and read-only. Unarchive it to make changes.
          </v-alert>
          <v-sheet v-if="project?.description" class="pa-3 rounded mt-2" border>
            <div class="text-caption text-medium-emphasis mb-1">Description</div>
            <div class="text-body-2">{{ project.description }}</div>
          </v-sheet>
        </v-sheet>
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

    <v-dialog v-model="whitelistDialog" max-width="700">
      <v-card>
        <v-card-title class="text-h6">Edit Multiinstallable Whitelist</v-card-title>
        <v-card-text>
          <p class="text-body-2 pb-3">
            Empty whitelist means all multiinstallable applications are launchable for project-PIs.
          </p>
          <v-checkbox
            v-for="item in allMultiinstallableExtensions"
            :key="item.releaseName"
            v-model="editableProjectWhitelist"
            :value="item.releaseName"
            hide-details
            class="my-1"
          >
            <template #label>
              <span>{{ item.annotations?.["ui-visible-name"] || item.releaseName }}</span>
              <span class="ml-2 text-medium-emphasis" style="font-family: monospace">({{ item.releaseName }})</span>
            </template>
          </v-checkbox>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="whitelistDialog = false">Cancel</v-btn>
          <v-btn color="primary" @click="saveWhitelist">Save</v-btn>
        </v-card-actions>
      </v-card>
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
import { aiiApiGet, aiiApiPost, aiiApiDelete, aiiApiPut, kubeHelmGet, kubeHelmPost } from '@/common/services';
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
import { useCookies } from 'vue3-cookies';
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
      whitelistDialog: false,

      allMultiinstallableExtensions: [] as any[],
      editableProjectWhitelist: [] as string[],

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
      const { cookies } = useCookies();
      try {
        const project: ProjectItem = await aiiApiGet(`projects/${this.projectId}`);
        this.project = project;
        cookies.set('Project', JSON.stringify({ name: project.name, id: project.id }));
        if (!silent) {
          this.notify(`Selected project: ${project.name}. You may need to refresh other tabs.`, 'success');
        }
        usePermissionsStore().loadProjectWhitelist(this.projectId);
        this.loadMultiinstallableExtensions();
      } catch (error) {
        console.error('Failed to load project:', error);
      }
    },

    async loadMultiinstallableExtensions(): Promise<void> {
      try {
        const extensions = await kubeHelmGet('extensions');
        this.allMultiinstallableExtensions = extensions
          .filter((e: any) => e.multiinstallable === 'yes')
          .sort((a: any, b: any) => a.releaseName.localeCompare(b.releaseName));
      } catch (error) {
        console.error('Failed to load extensions:', error);
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

    openWhitelistDialog(): void {
      this.editableProjectWhitelist = [...(this.project?.multiinstallable_whitelist ?? [])];
      this.whitelistDialog = true;
    },

    async saveWhitelist(): Promise<void> {
      try {
        await aiiApiPut(
          `projects/${this.projectId}/multiinstallable-whitelist`,
          {},
          { app_names: this.editableProjectWhitelist },
        );
        await this.loadProject();
        this.whitelistDialog = false;
      } catch (error) {
        console.error(error);
        this.notify('Failed to save whitelist.', 'error');
      }
    },
  },
});
</script>
