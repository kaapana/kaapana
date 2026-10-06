<template>
  <v-container fluid class="pm-view">
    <div class="mb-2">
      <v-btn variant="text" :prepend-icon="projectIcons.back" @click="$router.push('/')">
        Projects
      </v-btn>
    </div>

    <div class="d-flex flex-wrap align-start justify-space-between ga-4 mb-4">
      <h1 class="text-h4">Edit Role Rights</h1>
      <div class="d-flex flex-wrap align-center ga-2">
        <v-chip v-if="pendingCount > 0" color="warning" variant="tonal">
          {{ pendingCount }} unsaved change{{ pendingCount !== 1 ? 's' : '' }}
        </v-chip>
        <v-btn
          variant="outlined"
          color="error"
          :prepend-icon="projectIcons.reset"
          :loading="resetting"
          @click="askReset"
        >
          Reset to Defaults
        </v-btn>
        <v-btn :prepend-icon="kaapanaIcons.add" variant="outlined" @click="addRightDialog = true">
          Add Right
        </v-btn>
        <v-btn
          :disabled="pendingCount === 0 || saving"
          :loading="saving"
          color="primary"
          :prepend-icon="kaapanaIcons.save"
          @click="askSave"
        >
          Save Changes
        </v-btn>
      </div>
    </div>

    <v-alert type="info" variant="tonal" density="compact" class="mb-4">
      Changes are staged locally until you click <strong>Save Changes</strong>. Users receive
      updated rights when their session next refreshes, within a few minutes, or at their next
      login.
    </v-alert>

    <v-skeleton-loader v-if="loading" type="table" />

    <FailureAlert
      v-else-if="loadError"
      title="Role rights not loaded"
      text="Could not load the roles and rights."
      :error="loadError"
      :retry="load"
    />

    <v-card v-else :elevation="2">
      <v-table density="comfortable">
        <thead>
          <tr>
            <th>Right</th>
            <th class="text-caption text-medium-emphasis">JWT Claim</th>
            <th v-for="role in roles" :key="role.id" class="text-center">
              <div class="font-weight-medium text-uppercase">{{ role.name }}</div>
              <div class="text-caption text-medium-emphasis font-weight-regular text-wrap">
                {{ role.description }}
              </div>
            </th>
            <th class="text-right"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="right in rights" :key="right.id">
            <td>
              <v-tooltip :text="right.description" location="right">
                <template #activator="{ props }">
                  <span v-bind="props" class="font-weight-medium">{{ right.name }}</span>
                </template>
              </v-tooltip>
            </td>
            <td class="text-caption text-medium-emphasis">
              <span>{{ right.claim_key }}: {{ right.claim_value }}</span>
            </td>
            <td
              v-for="role in roles"
              :key="role.id"
              class="text-center"
              :class="isPending(role.id, right.id) ? 'pm-pending' : ''"
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
                <v-tooltip text="Delete right" location="top">
                  <template #activator="{ props }">
                    <v-btn
                      v-bind="props"
                      :icon="kaapanaIcons.delete"
                      :aria-label="`Delete right ${right.name}`"
                      :loading="deletingRightId === right.id"
                      :disabled="deletingRightId !== null"
                      size="default"
                      variant="text"
                      color="error"
                      @click="askDeleteRight(right)"
                    />
                  </template>
                </v-tooltip>
              </div>
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card>
  </v-container>

  <v-dialog v-model="addRightDialog" max-width="600">
    <v-card title="Add New Right">
      <v-card-text>
        <v-form ref="addRightForm" @submit.prevent="addRight">
          <v-text-field
            v-model="newRight.name"
            label="Name"
            hint="e.g. manage_users"
            :rules="[required('a name for the right, such as manage_users')]"
          />
          <v-text-field
            v-model="newRight.description"
            label="Description"
            :rules="[required('a description')]"
          />
          <v-text-field
            v-model="newRight.claim_key"
            label="JWT claim key"
            hint="e.g. kaapana.ai/aii"
            :rules="[required('the JWT claim key')]"
          />
          <v-text-field
            v-model="newRight.claim_value"
            label="JWT claim value"
            hint="e.g. manage_users"
            :rules="[required('the JWT claim value')]"
          />
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn :disabled="addingRight" @click="addRightDialog = false">Cancel</v-btn>
        <v-btn color="primary" :loading="addingRight" :disabled="addingRight" @click="addRight">
          Add right
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <ConfirmDialog
    v-model="confirmOpen"
    :color="confirmation.color"
    :title="confirmation.title"
    :text="confirmation.text"
    :confirm-text="confirmation.confirmText"
    @confirm="runConfirmed"
  />
</template>

<script lang="ts">
import { kaapanaIcons, projectIcons } from '@/utils/projectIcons'
import { ConfirmDialog } from '@kaapana/base-ui'
import { useConfirmation } from '@/composables/useConfirmation'
import { useViewDirty } from '@/composables/useViewDirty'
import { notify } from '@kyvg/vue3-notification'
import { notifyFailure } from '@/utils/notifyFailure'
import FailureAlert from '@/components/FailureAlert.vue'
import { defineComponent, ref } from 'vue'
import { aiiApiGet, aiiApiPost, aiiApiDelete } from '@/common/services'
import { required } from '@/common/validation'

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
  components: { ConfirmDialog, FailureAlert },
  setup() {
    const { confirmOpen, confirmation, ask, runConfirmed } = useConfirmation()
    const dirty = ref(false)
    useViewDirty(dirty)
    return {
      kaapanaIcons,
      projectIcons,
      confirmOpen,
      confirmation,
      ask,
      runConfirmed,
      dirty,
      required,
    }
  },
  data() {
    return {
      loading: true,
      saving: false,
      resetting: false,
      addRightDialog: false,
      addingRight: false,
      newRight: { name: '', description: '', claim_key: '', claim_value: '' },
      roles: [] as Role[],
      rights: [] as Right[],
      // committed state from DB: matrix[roleId] = Set of rightIds
      committed: {} as Record<number, Set<number>>,
      // pending overrides: key="${roleId}-${rightId}", value = desired boolean
      pending: {} as Record<string, boolean>,
      loadError: null as unknown,
      deletingRightId: null as number | null,
    }
  },

  computed: {
    pendingCount(): number {
      return Object.keys(this.pending).length;
    },
  },

  watch: {
    pendingCount(count: number) {
      this.dirty = count > 0
    },
  },

  mounted() {
    this.load()
  },

  methods: {
    async addRight() {
      const form = this.$refs.addRightForm as { validate: () => Promise<{ valid: boolean }> }
      if (!(await form.validate()).valid) return
      this.addingRight = true
      try {
        await aiiApiPost('projects/rights', this.newRight)
        notify({ type: 'success', text: `Right "${this.newRight.name}" added.` })
        this.addRightDialog = false
        this.newRight = { name: '', description: '', claim_key: '', claim_value: '' }
        await this.load()
      } catch (error: unknown) {
        notifyFailure('Right not added', `Could not add the right "${this.newRight.name}".`, error)
      } finally {
        this.addingRight = false;
      }
    },

    askDeleteRight(right: Right) {
      this.ask({
        color: 'error',
        title: `Delete right "${right.name}"?`,
        text:
          'The right is removed from every role that holds it, and users lose its claim when ' +
          'their session next refreshes, within a few minutes. Reset to Defaults restores ' +
          'default rights, not custom ones.',
        confirmText: 'Delete right',
        action: () => this.deleteRight(right),
      })
    },

    askReset() {
      this.ask({
        color: 'error',
        title: 'Reset role rights to defaults?',
        text:
          'All rights and role-right assignments are replaced by the defaults from the ' +
          'configuration; custom rights are permanently deleted. Unsaved staged changes are ' +
          'discarded.',
        confirmText: 'Reset to defaults',
        action: () => this.resetToDefaults(),
      })
    },

    askSave() {
      const count = this.pendingCount
      this.ask({
        color: 'primary',
        title: 'Save role-right changes?',
        text:
          `${count} change${count !== 1 ? 's are' : ' is'} applied to the role-rights mapping. ` +
          'Users receive the updated rights when their session next refreshes, within a few ' +
          'minutes.',
        confirmText: 'Save changes',
        action: () => this.saveChanges(),
      })
    },

    async deleteRight(right: Right) {
      this.deletingRightId = right.id
      try {
        await aiiApiDelete(`projects/rights/${right.id}`)
        notify({ type: 'success', text: `Right "${right.name}" deleted.` })
        await this.load()
      } catch (error: unknown) {
        notifyFailure('Right not deleted', `Could not delete the right "${right.name}".`, error)
      } finally {
        this.deletingRightId = null
      }
    },

    async resetToDefaults() {
      this.resetting = true
      try {
        const result = await aiiApiPost('projects/rights/reset', {})
        notify({
          type: 'success',
          text: `Reset complete: ${result.reset} role-right assignments applied.`,
        })
        await this.load()
      } catch (error: unknown) {
        notifyFailure('Role rights not reset', 'Could not reset the role rights.', error)
      } finally {
        this.resetting = false;
      }
    },

    async load() {
      this.loading = true
      this.loadError = null
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
        this.loadError = error
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

    async saveChanges() {
      this.saving = true
      let applied = 0
      let failed = 0
      let lastError: unknown = null

      try {
        await Promise.all(
          Object.entries(this.pending).map(async ([key, grant]) => {
            const [roleId, rightId] = key.split('-').map(Number);
            try {
              if (grant) {
                await aiiApiPost(`projects/roles/${roleId}/rights/${rightId}`, {});
              } else {
                await aiiApiDelete(`projects/roles/${roleId}/rights/${rightId}`);
              }
              applied++
            } catch (error) {
              lastError = error
              failed++
            }
          })
        );

        if (failed > 0) {
          notifyFailure(
            'Role rights partly saved',
            `${applied} change${applied !== 1 ? 's' : ''} saved, ${failed} failed.`,
            lastError,
          )
        } else {
          notify({
            type: 'success',
            text: `${applied} change${applied !== 1 ? 's' : ''} saved. Users receive the updated rights within a few minutes.`,
          })
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
