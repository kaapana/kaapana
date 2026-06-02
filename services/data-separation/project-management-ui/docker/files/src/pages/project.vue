<template>
  <v-snackbar v-model="isSnackbarVisible" :timeout="10000" location="top" :color="snackbarColor" elevation="2">
    {{ snackbarMessage }}
  </v-snackbar>

  <v-container max-width="1200" class="bg-surface rounded-lg mt-2">

    <!-- ── Back navigation ──────────────────────────────────────── -->
    <v-row no-gutters class="mb-4">
      <v-col>
        <v-btn size="x-small" variant="outlined" prepend-icon="mdi-arrow-left" @click="goToProjectsList">
          Back to Projects
        </v-btn>
      </v-col>
    </v-row>

    <!-- ── Project header card ──────────────────────────────────── -->
    <v-row>
      <v-col>
        <v-sheet class="pa-4 rounded-lg" border>
          <div v-if="project" class="d-flex align-center ga-3 mb-3">
            <v-icon icon="mdi-folder-multiple" color="primary" size="large" />
            <div class="d-flex flex-column flex-grow-1">
              <div class="d-flex align-baseline ga-2">
                <span class="text-h5">Project:</span>
                <span class="text-h5 font-weight-bold ml-2">{{ project.name }}</span>
              </div>
            </div>
          </div>
          <v-sheet v-if="project?.description" class="pa-3 rounded" border>
            <div class="text-caption text-medium-emphasis mb-1">Description</div>
            <div class="text-body-2">{{ project.description }}</div>
          </v-sheet>
          <v-skeleton-loader v-else :loading="!project" type="heading, paragraph" />
        </v-sheet>
      </v-col>
    </v-row>

    <!-- ── Project Users ────────────────────────────────────────── -->
    <v-row>
      <ProjectUsers :project="project" :expanded="isUsersSectionExpanded" @toggle="isUsersSectionExpanded = $event" />
    </v-row>

    <v-divider class="my-4" />

    <!-- ── Executable Workflows ─────────────────────────────────── -->
    <v-row>
      <ProjectWorkflows :project="project" :expanded="isWorkflowsSectionExpanded"
        @toggle="isWorkflowsSectionExpanded = $event" />
    </v-row>

    <v-divider class="my-4" />

    <!-- ── Multiinstallable Applications ────────────────────────── -->
    <v-row>
      <MultiinstallableApplications :project="project" :expanded="isAppsSectionExpanded"
        @toggle="isAppsSectionExpanded = $event" />
    </v-row>

    <v-divider class="my-4" />

    <!-- ── Active Project Applications ──────────────────────────── -->
    <v-row v-if="can(project?.id, 'view_active_apps')">
      <ActiveProjectApplications :project="project" :expanded="isActiveAppsSectionExpanded"
        @toggle="isActiveAppsSectionExpanded = $event" @confirm-uninstall="confirmAppUninstall" />
    </v-row>

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
              <span class="ml-2 text-medium-emphasis">({{ item.releaseName }})</span>
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
    this.loadAdminAccess();
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

    loadAdminAccess(): void {
      const permissionsStore = usePermissionsStore();
      const check = setInterval(() => {
        const store = (this as any).$store;
        const user = store?.state?.user;
        if (user) {
          permissionsStore.loadUserRights(user.id);
          if (user.realm_roles?.includes('admin') || user.realm_roles?.includes('project-manager')) {
            this.userHasAdminAccess = true;
            permissionsStore.admin = true;
          }
          clearInterval(check);
        }
      }, 100);
    },

    goToProjectsList(): void {
      this.$router.push('/');
    },

    async loadProject(): Promise<void> {
      if (!this.projectId) return;
      const { cookies } = useCookies();
      try {
        const project: ProjectItem = await aiiApiGet(`projects/${this.projectId}`);
        this.project = project;
        cookies.set('Project', JSON.stringify({ name: project.name, id: project.id }));
        this.notify(`Selected project: ${project.name}. You may need to refresh other tabs.`, 'success');
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
      const permissionsStore = usePermissionsStore();
      if (
        !permissionsStore.hasRight(this.project?.id, 'delete_multiinstallable') &&
        !permissionsStore.hasRight(this.project?.id, 'manage_project_extensions')
      ) return;
      try {
        await kubeHelmPost('helm-delete-chart', { release_name: app.release_name });
      } catch (error) {
        console.error('Failed to uninstall application:', error);
        this.notify('Failed to uninstall application.', 'error');
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
