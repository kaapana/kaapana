<template>
  <v-snackbar v-model="snackbarVisible" :timeout="4000" location="top" :color="snackbarColor" elevation="2" closable>
    {{ snackbarMessage }}
  </v-snackbar>

  <v-container max-width="1400" class="bg-surface rounded-lg mt-2">

    <!-- ── Back navigation ──────────────────────────────────────── -->
    <v-row no-gutters class="mb-2">
      <v-col>
        <v-btn size="x-small" variant="outlined" prepend-icon="mdi-arrow-left" @click="$router.push('/')">
          Projects
        </v-btn>
      </v-col>
    </v-row>

    <!-- ── Header card ──────────────────────────────────────────── -->
    <v-row class="mb-4">
      <v-col>
        <v-sheet class="pa-4 rounded-lg" border>
          <div class="d-flex align-center justify-space-between">
            <div class="d-flex align-center ga-3">
              <v-icon icon="mdi-shield-key" color="primary" size="large" />
              <span class="text-h5 font-weight-bold">Edit Role Rights</span>
            </div>
            <div class="d-flex align-center ga-2">
              <v-chip v-if="pendingCount > 0" color="warning" variant="tonal">
                {{ pendingCount }} unsaved change{{ pendingCount !== 1 ? 's' : '' }}
              </v-chip>
              <v-btn
                variant="outlined"
                size="large"
                prepend-icon="mdi-restore"
                :loading="resetting"
                @click="resetDialog = true"
              >
                Reset to Defaults
              </v-btn>
              <v-btn
                size="large"
                prepend-icon="mdi-plus"
                variant="outlined"
                @click="addRightDialog = true"
              >
                Add Right
              </v-btn>
              <v-btn
                :disabled="pendingCount === 0 || saving"
                :loading="saving"
                color="primary"
                size="large"
                prepend-icon="mdi-content-save"
                @click="confirmDialog = true"
              >
                Save Changes
              </v-btn>
            </div>
          </div>
        </v-sheet>
      </v-col>
    </v-row>

    <v-alert v-if="userLoaded && !isAdmin" type="error" class="mb-4">
      This page is only accessible to admins.
    </v-alert>

    <template v-else>
      <v-alert type="info" variant="tonal" density="compact" class="mb-4">
        Changes are staged locally until you click <strong>Save Changes</strong>.
        Users receive updated rights on their next login or when their token refreshes (within ~15 minutes).
      </v-alert>

      <v-skeleton-loader v-if="loading" type="table" />

      <v-table v-else density="comfortable" class="rounded">
        <thead>
          <tr>
            <th style="width: 150px">Right</th>
            <th style="width: 150px" class="text-caption text-medium-emphasis">JWT Claim</th>
            <th
              v-for="role in roles"
              :key="role.id"
              class="text-center"
              style="width: 130px"
            >
              <div class="font-weight-bold text-uppercase">{{ role.name }}</div>
              <div class="text-caption text-medium-emphasis font-weight-regular" style="white-space: normal; line-height: 1.3">
                {{ role.description }}
              </div>
            </th>
            <th style="width: 48px" class="text-right"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="right in rights" :key="right.id">
            <td>
              <v-tooltip :text="right.description" location="right">
                <template #activator="{ props }">
                  <span v-bind="props" class="font-weight-medium" style="font-family: monospace">{{ right.name }}</span>
                </template>
              </v-tooltip>
            </td>
            <td class="text-caption text-medium-emphasis">
              <span style="font-family: monospace">{{ right.claim_key }}: {{ right.claim_value }}</span>
            </td>
            <td
              v-for="role in roles"
              :key="role.id"
              class="text-center"
              :class="isPending(role.id, right.id) ? 'bg-warning-lighten-4' : ''"
            >
              <v-checkbox-btn
                :model-value="effectiveValue(role.id, right.id)"
                color="primary"
                hide-details
                density="compact"
                inline
                @update:model-value="stage(role.id, right.id, $event)"
              />
            </td>
            <td>
              <div class="d-flex justify-end pr-2">
                <v-btn icon="mdi-trash-can" size="default" variant="text" color="error" @click="deleteRight(right)" />
              </div>
            </td>
          </tr>
        </tbody>
      </v-table>
    </template>
  </v-container>

  <!-- Reset to defaults dialog -->
  <v-dialog v-model="resetDialog" max-width="480">
    <v-card rounded="lg">
      <v-card-title class="text-h6 pa-6 pb-2">Reset to defaults?</v-card-title>
      <v-card-text class="pa-6 pt-2">
        This will:
        <ul class="mt-2 ml-4">
          <li>Recreate any missing default rights from the configmap</li>
          <li><strong>Permanently delete</strong> any custom rights you added</li>
          <li>Reset all role-rights assignments to the configmap defaults</li>
        </ul>
        <div class="mt-3">Any unsaved staged changes will also be discarded.</div>
      </v-card-text>
      <v-card-actions class="pa-4 pt-0">
        <v-spacer />
        <v-btn variant="text" @click="resetDialog = false">Cancel</v-btn>
        <v-btn color="error" variant="flat" :loading="resetting" @click="resetToDefaults">
          Reset
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Add right dialog -->
  <v-dialog v-model="addRightDialog" max-width="520">
    <v-card rounded="lg">
      <v-card-title class="text-h6 pa-6 pb-2">Add New Right</v-card-title>
      <v-card-text class="pa-6 pt-2 d-flex flex-column ga-3">
        <v-text-field v-model="newRight.name" label="Name" hint="e.g. manage_users" density="compact" variant="outlined" />
        <v-text-field v-model="newRight.description" label="Description" density="compact" variant="outlined" />
        <v-text-field v-model="newRight.claim_key" label="JWT Claim Key" hint="e.g. kaapana.ai/aii" density="compact" variant="outlined" />
        <v-text-field v-model="newRight.claim_value" label="JWT Claim Value" hint="e.g. manage_users" density="compact" variant="outlined" />
      </v-card-text>
      <v-card-actions class="pa-4 pt-0">
        <v-spacer />
        <v-btn variant="text" @click="addRightDialog = false">Cancel</v-btn>
        <v-btn color="primary" variant="flat" :loading="addingRight" @click="addRight">Add</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Confirm dialog -->
  <v-dialog v-model="confirmDialog" max-width="480">
    <v-card rounded="lg">
      <v-card-title class="text-h6 pa-6 pb-2">Save changes?</v-card-title>
      <v-card-text class="pa-6 pt-2">
        This will apply <strong>{{ pendingCount }} change{{ pendingCount !== 1 ? 's' : '' }}</strong>
        to the role-rights mapping. Users will receive the updated rights on their next login or token refresh.
      </v-card-text>
      <v-card-actions class="pa-4 pt-0">
        <v-spacer />
        <v-btn variant="text" @click="confirmDialog = false">Cancel</v-btn>
        <v-btn color="primary" variant="flat" :loading="saving" @click="saveAndLogout">
          Save
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { aiiApiGet, aiiApiPost, aiiApiDelete } from '@/common/services';
import { isAdminUser, waitForStoreUser } from '@/common/userAccess';

interface Right {
  id: number;
  name: string;
  description: string;
  claim_key: string;
  claim_value: string;
}

interface Role {
  id: number;
  name: string;
  description: string;
}

export default defineComponent({
  data() {
    return {
      isAdmin: false,
      userLoaded: false,
      loading: true,
      saving: false,
      resetting: false,
      confirmDialog: false,
      resetDialog: false,
      addRightDialog: false,
      addingRight: false,
      newRight: { name: '', description: '', claim_key: '', claim_value: '' },
      roles: [] as Role[],
      rights: [] as Right[],
      // committed state from DB: matrix[roleId] = Set of rightIds
      committed: {} as Record<number, Set<number>>,
      // pending overrides: key="${roleId}-${rightId}", value = desired boolean
      pending: {} as Record<string, boolean>,
      snackbarVisible: false,
      snackbarMessage: '',
      snackbarColor: 'info',
    };
  },

  computed: {
    pendingCount(): number {
      return Object.keys(this.pending).length;
    },
  },

  mounted() {
    waitForStoreUser((user) => {
      this.isAdmin = isAdminUser(user);
      this.userLoaded = true;
      if (this.isAdmin) this.load();
      else this.loading = false;
    });
  },

  methods: {
    async addRight() {
      if (!this.newRight.name) return;
      this.addingRight = true;
      try {
        await aiiApiPost('projects/rights', this.newRight);
        this.notify(`Right "${this.newRight.name}" added.`, 'success');
        this.addRightDialog = false;
        this.newRight = { name: '', description: '', claim_key: '', claim_value: '' };
        await this.load();
      } catch (error: any) {
        const detail = error?.response?.data?.detail ?? error?.message ?? 'Unknown error';
        this.notify(`Failed to add right: ${detail}`, 'error');
      } finally {
        this.addingRight = false;
      }
    },

    async deleteRight(right: { id: number; name: string }) {
      try {
        await aiiApiDelete(`projects/rights/${right.id}`);
        this.notify(`Right "${right.name}" deleted.`, 'success');
        await this.load();
      } catch (error: any) {
        const detail = error?.response?.data?.detail ?? error?.message ?? 'Unknown error';
        this.notify(`Failed to delete right: ${detail}`, 'error');
      }
    },

    async resetToDefaults() {
      this.resetting = true;
      this.resetDialog = false;
      try {
        const result = await aiiApiPost('projects/rights/reset', {});
        this.notify(`Reset complete: ${result.reset} role-right assignments applied.`, 'success');
        await this.load();
      } catch (error: any) {
        const detail = error?.response?.data?.detail ?? error?.message ?? 'Unknown error';
        this.notify(`Reset failed: ${detail}`, 'error');
      } finally {
        this.resetting = false;
      }
    },

    notify(msg: string, color = 'info') {
      this.snackbarMessage = msg;
      this.snackbarColor = color;
      this.snackbarVisible = true;
    },

    async load() {
      this.loading = true;
      try {
        const [roles, rights] = await Promise.all([
          aiiApiGet('projects/roles'),
          aiiApiGet('projects/rights'),
        ]);
        this.roles = roles;
        this.rights = rights;

        const committed: Record<number, Set<number>> = {};
        await Promise.all(
          roles.map(async (role: Role) => {
            const roleRights: Right[] = await aiiApiGet(`projects/roles/${role.id}/rights`);
            committed[role.id] = new Set(roleRights.map((r) => r.id));
          })
        );
        this.committed = committed;
        this.pending = {};
      } catch (error) {
        console.error('Failed to load role rights:', error);
        this.notify('Failed to load role rights.', 'error');
      } finally {
        this.loading = false;
      }
    },

    // Effective value: pending overrides committed
    effectiveValue(roleId: number, rightId: number): boolean {
      const key = `${roleId}-${rightId}`;
      if (key in this.pending) return this.pending[key];
      return this.committed[roleId]?.has(rightId) ?? false;
    },

    isPending(roleId: number, rightId: number): boolean {
      return `${roleId}-${rightId}` in this.pending;
    },

    stage(roleId: number, rightId: number, value: boolean) {
      const key = `${roleId}-${rightId}`;
      const original = this.committed[roleId]?.has(rightId) ?? false;
      if (value === original) {
        // Reverted to original — remove from pending
        const { [key]: _, ...rest } = this.pending;
        this.pending = rest;
      } else {
        this.pending = { ...this.pending, [key]: value };
      }
    },

    async saveAndLogout() {
      this.saving = true;
      this.confirmDialog = false;
      let applied = 0;
      let failed = 0;

      try {
        await Promise.all(
          Object.entries(this.pending).map(async ([key, grant]) => {
            const [roleId, rightId] = key.split('-').map(Number);
            try {
              if (grant) {
                await aiiApiPost(`projects/roles/${roleId}/right/${rightId}`, {});
              } else {
                await aiiApiDelete(`projects/roles/${roleId}/right/${rightId}`);
              }
              applied++;
            } catch (e: any) {
              console.error(`Failed to update ${key}:`, e);
              failed++;
            }
          })
        );

        if (failed > 0) {
          this.notify(`${applied} change${applied !== 1 ? 's' : ''} saved, ${failed} failed.`, 'warning');
        } else {
          this.notify(
            `${applied} change${applied !== 1 ? 's' : ''} saved. Users will receive updated rights on their next login or token refresh.`,
            'success'
          );
        }

        // Reload committed state
        await this.load();
      } finally {
        this.saving = false;
      }
    },
  },
});
</script>
