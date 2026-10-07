<template>
    <v-col>
        <!-- ── Section header ─────────────────────────────────────── -->
        <SectionHeader :expanded="props.expanded" @toggle="emit('toggle', $event)">
            <!-- LEFT TITLE -->
            <template #title>
                Project Users
            </template>

            <!-- OPTIONAL CHIP -->
            <template #meta>
                <v-chip v-if="filteredUsers.length > 0" size="small" color="primary" variant="tonal">
                    {{ filteredUsers.length }}
                </v-chip>
            </template>

            <!-- RIGHT ACTIONS -->
            <template #actions>

                <!-- system users toggle -->
                <v-tooltip v-if="isAdmin" location="top">
                    <template #activator="{ props }">
                        <div class="d-flex align-center ga-2" v-bind="props">
                            <v-icon
                                :color="showSystemUsers ? 'primary' : 'medium-emphasis'"
                                :icon="projectIcons.systemUsers"
                            />

                            <v-switch
                                v-model="showSystemUsers"
                                aria-label="Show system users"
                                hide-details
                                inset
                                density="compact"
                                color="primary"
                            />
                        </div>
                    </template>

                    <span>Show system users</span>
                </v-tooltip>

                <!-- add button -->
                <v-btn
                    v-if="can(project?.id, 'manage_users')"
                    :disabled="readOnly"
                    color="primary"
                    :prepend-icon="projectIcons.addUser"
                    @click.stop="openAddUserDialog"
                >
                    Add User
                </v-btn>

            </template>
        </SectionHeader>

        <!-- ── Expanded content ────────────────────────────────────── -->
        <v-expand-transition>
            <div v-if="props.expanded">
                <!-- search -->
                <SearchBar v-model="search" label="Search users" />
                <FailureAlert
                    v-if="loadError"
                    title="Members not loaded"
                    text="Could not load the members of this project."
                    :error="loadError"
                    :retry="loadProjectUsers"
                />

                <!-- User table -->
                <v-data-table
                    v-else
                    :loading="isLoadingUsers"
                    loading-text="Loading members…"
                    :items-per-page="-1"
                    hide-default-footer
                    :headers="tableHeaders"
                    :items="filteredUsers"
                    :sort-by="[{ key: 'username', order: 'asc' }]"
                    multi-sort
                    class="mt-4"
                >
                    <template #item.icon>
                        <v-icon :icon="kaapanaIcons.account" />
                    </template>

                    <template #item.role="{ item }">
                        <v-tooltip location="top">
                            <template #activator="{ props }">
                                <span v-bind="props">{{ item.role?.name }}</span>
                            </template>

                            <span v-if="item.role?.name === 'principal-investigator'">
                                Principal Investigator: Has full access and control over the project.
                            </span>

                            <span v-else-if="item.role?.name === 'scientist'">
                                Scientist: Can use approved software for research purposes.
                            </span>

                            <span v-else>
                                {{ item.role?.name }}
                            </span>
                        </v-tooltip>
                    </template>

                    <template #item.actions="{ item }">
                        <div class="d-flex justify-center ga-1">
                            <v-tooltip text="Change role" location="top">
                                <template #activator="{ props }">
                                    <v-btn
                                        v-bind="props"
                                        @click="openEditUserDialog(item)"
                                        :icon="projectIcons.editRole"
                                        :aria-label="`Change role of ${item.username}`"
                                        color="primary"
                                        variant="text"
                                        :disabled="removingUserId !== null || readOnly"
                                    />
                                </template>
                            </v-tooltip>
                            <v-tooltip text="Remove from project" location="top">
                                <template #activator="{ props }">
                                    <v-btn
                                        v-bind="props"
                                        @click="onRemoveUser(item)"
                                        :icon="kaapanaIcons.delete"
                                        :aria-label="`Remove ${item.username} from the project`"
                                        :loading="removingUserId === item.id"
                                        color="error"
                                        variant="text"
                                        :disabled="removingUserId !== null || readOnly"
                                    />
                                </template>
                            </v-tooltip>
                        </div>
                    </template>
                    <template #no-data>
                        <ListEmptyState
                            :search="search.trim()"
                            noun="members"
                            title="No members yet"
                            text="Add users to give them access to this project."
                            @clear-search="search = ''"
                        >
                            <template v-if="can(project?.id, 'manage_users')" #actions>
                                <v-btn
                                    :disabled="readOnly"
                                    color="primary"
                                    variant="text"
                                    :prepend-icon="projectIcons.addUser"
                                    @click="openAddUserDialog"
                                >
                                    Add User
                                </v-btn>
                            </template>
                        </ListEmptyState>
                    </template>
                </v-data-table>
            </div>
        </v-expand-transition>

        <!-- ── Add users dialog ────────────────────────────────────── -->
        <GuardedDialog
            v-slot="{ requestClose }"
            v-model="isAddDialogOpen"
            :dirty="addDirty"
            max-width="600"
        >
            <AddUserToProject
                v-if="isAddDialogOpen"
                :project="project"
                action-type="add"
                :existing-user-ids="users.map((u) => u.id)"
                @cancel="requestClose"
                @update:dirty="addDirty = $event"
                @success="onUserOperationSuccess"
            />
        </GuardedDialog>

        <!-- ── Edit user role dialog ───────────────────────────────── -->
        <GuardedDialog
            v-slot="{ requestClose }"
            v-model="isEditDialogOpen"
            :dirty="editDirty"
            max-width="600"
        >
            <AddUserToProject
                v-if="isEditDialogOpen && selectedUser"
                :project="project"
                action-type="update"
                :user-to-edit="selectedUser"
                :existing-user-ids="users.filter((u) => u.id !== selectedUser!.id).map((u) => u.id)"
                @cancel="requestClose"
                @update:dirty="editDirty = $event"
                @success="onUserOperationSuccess"
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
    </v-col>
</template>

<script lang="ts" setup>
import { kaapanaIcons, projectIcons } from '@/utils/projectIcons'
import { ref, onMounted, watch, computed } from 'vue'
import { UserItem, UserRole } from '@/common/types'
import { usePermissions } from '@/permissions/usePermissions'
import { aiiApiDelete, aiiApiGet } from '@/common/services'
import { isAdminUser, isSystemUser, waitForStoreUser } from '@/common/userAccess'
import AddUserToProject from './AddUserToProject.vue'
import SearchBar from '@/components/SearchBar.vue'
import SectionHeader from '@/components/SectionHeader.vue'
import GuardedDialog from '@/components/GuardedDialog.vue'
import ListEmptyState from '@/components/ListEmptyState.vue'
import { ConfirmDialog } from '@kaapana/base-ui'
import { useConfirmation } from '@/composables/useConfirmation'
import { notify } from '@kyvg/vue3-notification'
import { notifyFailure } from '@/utils/notifyFailure'
import FailureAlert from '@/components/FailureAlert.vue'
// ── Types ──────────────────────────────────────────────────────────────────

interface UserWithRole extends UserItem {
    role?: UserRole;
}

interface ProjectRef {
    id?: string
    name?: string
    is_archived?: boolean
}

// ── Props & emits ──────────────────────────────────────────────────────────

const props = defineProps<{
    project: ProjectRef | null;
    expanded: boolean;
}>();

const emit = defineEmits<{
    (e: 'toggle', value: boolean): void;
}>();

// ── Permissions ────────────────────────────────────────────────────────────

const { can } = usePermissions()
const readOnly = computed(() => !!props.project?.is_archived)

// ── State ──────────────────────────────────────────────────────────────────

const search = ref('')
const users = ref<UserWithRole[]>([])
const isLoadingUsers = ref(false)
const loadError = ref<unknown>(null)
const removingUserId = ref<string | null>(null)

const isAddDialogOpen = ref(false)
const isEditDialogOpen = ref(false)
const addDirty = ref(false)
const editDirty = ref(false)

const selectedUser = ref<UserWithRole | undefined>(undefined)
const { confirmOpen, confirmation, ask, runConfirmed } = useConfirmation()

// ── System user filtering ──────────────────────────────────────────────────

const isAdmin = ref(false);
const showSystemUsers = ref(false);

const filteredUsers = computed(() => {
    let result = users.value;

    if (!showSystemUsers.value) {
        result = result.filter(u => !isSystemUser(u));
    }

    const q = search.value.trim().toLowerCase();
    if (!q) return result;

    return result.filter(u => {
        return (
            u.username?.toLowerCase().includes(q) ||
            u.first_name?.toLowerCase().includes(q) ||
            u.last_name?.toLowerCase().includes(q) ||
            u.email?.toLowerCase().includes(q) ||
            u.role?.name?.toLowerCase().includes(q)
        );
    });
});

// ── Table headers ──────────────────────────────────────────────────────────

const tableHeaders = computed(() => [
    { title: '', key: 'icon', width: '40px' },
    { title: 'Username', key: 'username' },
    { title: 'First Name', key: 'first_name' },
    { title: 'Last Name', key: 'last_name' },
    { title: 'Email', key: 'email' },
    { title: 'Role', key: 'role' },
    ...(can(props.project?.id, 'manage_users')
        ? [{ title: 'Actions', key: 'actions', width: '100px', align: 'center' as const }]
        : []),
])

// ── Lifecycle ──────────────────────────────────────────────────────────────

onMounted(() => {
    waitForStoreUser(user => { isAdmin.value = isAdminUser(user); });
    if (props.project?.id) loadProjectUsers();
});

watch(
    () => props.project?.id,
    (newId) => { if (newId) loadProjectUsers(); }
);

// ── Dialog helpers ─────────────────────────────────────────────────────────

const openAddUserDialog = () => { isAddDialogOpen.value = true; };

const openEditUserDialog = (user: UserWithRole) => {
    selectedUser.value = user;
    isEditDialogOpen.value = true;
};

const closeEditDialog = () => {
    isEditDialogOpen.value = false;
    selectedUser.value = undefined;
};

const onRemoveUser = (user: UserWithRole) => {
    ask({
        color: 'error',
        title: `Remove ${user.first_name} ${user.last_name} from "${props.project?.name}"?`,
        text:
            `@${user.username} loses access to this project when their session next refreshes, ` +
            'within a few minutes. ' +
            'Data in the project is not affected, and the user can be added again later.',
        confirmText: 'Remove user',
        action: () => removeUser(user),
    })
}

// ── User operations ────────────────────────────────────────────────────────

const removeUser = async (user: UserWithRole) => {
    if (!props.project?.id) return
    removingUserId.value = user.id
    try {
        await aiiApiDelete(`projects/${props.project.id}/user/${user.id}/rolemapping`)
        notify({ type: 'success', text: `@${user.username} removed from the project.` })
        // Reload to verify the change
        await loadProjectUsers({ showLoading: false });
    } catch (error) {
        notifyFailure('User not removed', `Could not remove @${user.username} from the project.`, error)
    } finally {
        removingUserId.value = null
    }
};

const onUserOperationSuccess = async () => {
    isAddDialogOpen.value = false;
    closeEditDialog();
    // Reload to verify the changes
    await loadProjectUsers({ showLoading: false });
};

// ── Data fetching ──────────────────────────────────────────────────────────

const loadProjectUsers = async (options: { showLoading?: boolean } = {}) => {
    if (!props.project?.id) return;
    if (options.showLoading !== false) {
        isLoadingUsers.value = true;
    }
    loadError.value = null
    try {
        const fetchedUsers: UserItem[] = await aiiApiGet(`projects/${props.project.id}/users`);
        users.value = fetchedUsers ?? [];
        await Promise.all(
            users.value.map((user, index) => loadUserRole(user.id, index))
        );
    } catch (error) {
        loadError.value = error
    } finally {
        if (options.showLoading !== false) {
            isLoadingUsers.value = false;
        }
    }
};

const loadUserRole = async (userId: string, userIndex: number) => {
    if (!props.project?.id) return
    const role: UserRole = await aiiApiGet(`projects/${props.project.id}/users/${userId}/roles`)
    if (users.value[userIndex]) users.value[userIndex].role = role
}
</script>
