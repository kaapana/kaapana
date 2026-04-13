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
                <v-tooltip location="top">
                    <template #activator="{ props }">
                        <div class="d-flex align-center ga-2" v-bind="props">

                            <v-icon :color="showSystemUsers ? 'primary' : 'text'">
                                mdi-account-cog
                            </v-icon>

                            <v-switch v-model="showSystemUsers" hide-details inset density="compact" color="primary" />
                        </div>
                    </template>

                    <span>Show system users</span>
                </v-tooltip>

                <!-- add button -->
                <v-btn v-if="can(project?.id, 'manage_project_users')" @click.stop="openAddUserDialog" size="large"
                    variant="outlined" color="primary" prepend-icon="mdi-account-plus">
                    Add User
                </v-btn>

            </template>
        </SectionHeader>

        <!-- ── Expanded content ────────────────────────────────────── -->
        <v-expand-transition>
            <div v-if="props.expanded">
                <!-- search -->
                <SearchBar v-model="search" placeholder="Search users..." />
                <!-- Loading skeleton -->
                <v-skeleton-loader v-if="isLoadingUsers" type="table" class="mt-4" />

                <!-- User table -->
                <v-data-table v-else-if="filteredUsers.length > 0" :headers="tableHeaders" :items="filteredUsers"
                    :sort-by="[{ key: 'username', order: 'asc' }]" multi-sort class="mt-4">

                    <template #item.icon="{ item }">
                        <td>
                            <v-icon>mdi-account-circle</v-icon>
                        </td>
                    </template>

                    <template #item.username="{ item }">
                        <td>{{ item.username }}</td>
                    </template>

                    <template #item.first_name="{ item }">
                        <td>{{ item.first_name }}</td>
                    </template>

                    <template #item.last_name="{ item }">
                        <td>{{ item.last_name }}</td>
                    </template>

                    <template #item.email="{ item }">
                        <td>{{ item.email }}</td>
                    </template>

                    <template #item.role="{ item }">
                        <td>
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
                        </td>
                    </template>

                    <template #item.actions="{ item }">
                        <td class="text-center">
                            <div class="d-flex justify-center gap-1">
                                <v-btn @click="openEditUserDialog(item)" icon="mdi-link-edit" />
                                <v-btn @click="onRemoveUser(item)" icon="mdi-trash-can" />
                            </div>
                        </td>
                    </template>
                </v-data-table>

                <!-- Empty state -->
                <v-sheet rounded v-else class="mt-4">
                    <v-container>
                        <v-row align="center" justify="center" no-gutters>
                            <v-icon icon="mdi-information" size="x-large" class="large-font"></v-icon>
                        </v-row>
                        <v-row align="center" justify="center" no-gutters class="py-6">
                            <div class="text-subtitle-1 font-weight-light text-center">
                                No User found under this Project. Click the following button to Add new user.
                            </div>
                        </v-row>
                        <v-row align="center" justify="center" no-gutters>
                            <v-btn @click="openAddUserDialog" size="large" variant="outlined"
                                prepend-icon="mdi-account-plus" v-if="can(project?.id, 'manage_project_users')">
                                Add user to project "{{ project?.name }}"
                            </v-btn>
                        </v-row>
                    </v-container>
                </v-sheet>

            </div>
        </v-expand-transition>

        <!-- ── Add users dialog ────────────────────────────────────── -->
        <v-dialog v-model="isAddDialogOpen" max-width="640" scrollable>
            <AddUserToProject v-if="isAddDialogOpen" :project="project" action-type="add"
                :existing-user-ids="users.map(u => u.id)" @cancel="closeAddDialog" @success="onUserOperationSuccess"
                @users-added="onUsersAdded" @users-add-failed="onUsersAddFailed" />
        </v-dialog>

        <!-- ── Edit user role dialog ───────────────────────────────── -->
        <v-dialog v-model="isEditDialogOpen" max-width="480" scrollable>
            <AddUserToProject v-if="isEditDialogOpen && selectedUser" :project="project" action-type="update"
                :user-to-edit="selectedUser"
                :existing-user-ids="users.filter(u => u.id !== selectedUser!.id).map(u => u.id)"
                @cancel="closeEditDialog" @success="onUserOperationSuccess" @role-updated="onRoleUpdated"
                @role-update-failed="onRoleUpdateFailed" />
        </v-dialog>

        <!-- ── Remove confirmation dialog ─────────────────────────── -->
        <v-dialog v-model="isRemoveDialogOpen" max-width="400">
            <v-card rounded="lg">
                <v-card-title class="text-h6 pa-6 pb-2">Remove user from project?</v-card-title>
                <v-card-text class="pa-6 pt-2">
                    <span v-if="userPendingRemoval">
                        This will remove
                        <strong>{{ userPendingRemoval.first_name }} {{ userPendingRemoval.last_name }}</strong>
                        (@{{ userPendingRemoval.username }}) from this project.
                        They will lose all access immediately.
                    </span>
                </v-card-text>
                <v-card-actions class="pa-4 pt-0">
                    <v-spacer />
                    <v-btn variant="text" @click="isRemoveDialogOpen = false">Cancel</v-btn>
                    <v-btn color="error" variant="flat" :loading="isRemoving" @click="confirmRemoveUser">
                        Remove
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>

    </v-col>
</template>

<script lang="ts" setup>
import { ref, onMounted, watch, computed } from 'vue';
import { UserItem, UserRole } from '@/common/types';
import { usePermissions } from '@/permissions/usePermissions';
import { aiiApiDelete, aiiApiGet } from '@/common/services';
import AddUserToProject from './AddUserToProject.vue';
import SearchBar from '@/components/SearchBar.vue';
// ── Types ──────────────────────────────────────────────────────────────────

interface UserWithRole extends UserItem {
    role?: UserRole;
}

interface ProjectRef {
    id?: string;
    name?: string;
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

const { can } = usePermissions();


// ── State ──────────────────────────────────────────────────────────────────

const search = ref('')
const users = ref<UserWithRole[]>([]);
const isLoadingUsers = ref(false);
const isRemoving = ref(false);

const isAddDialogOpen = ref(false);
const isEditDialogOpen = ref(false);
const isRemoveDialogOpen = ref(false);

const selectedUser = ref<UserWithRole | undefined>(undefined);
const userPendingRemoval = ref<UserWithRole | undefined>(undefined);

// ── System user filtering ──────────────────────────────────────────────────

// System users that should be hidden by default
const isSystemUser = (u: UserItem) => {
    const username = (u.username || '').toLowerCase();
    const lastName = (u.last_name || '').toLowerCase();

    return (
        lastName === 'system' ||
        username.endsWith('-system-user')
    );
};

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

const tableHeaders = [
    { title: '', key: 'icon', width: '40px' },
    { title: 'Username', key: 'username' },
    { title: 'First Name', key: 'first_name' },
    { title: 'Last Name', key: 'last_name' },
    { title: 'Email', key: 'email' },
    { title: 'Role', key: 'role' },
    { title: 'Actions', key: 'actions' }
];

// ── Lifecycle ──────────────────────────────────────────────────────────────

onMounted(() => {
    if (props.project?.id) loadProjectUsers();
});

watch(
    () => props.project?.id,
    (newId) => { if (newId) loadProjectUsers(); }
);

// ── Dialog helpers ─────────────────────────────────────────────────────────

const openAddUserDialog = () => { isAddDialogOpen.value = true; };

const closeAddDialog = () => {
    isAddDialogOpen.value = false;
};

const openEditUserDialog = (user: UserWithRole) => {
    selectedUser.value = user;
    isEditDialogOpen.value = true;
};

const closeEditDialog = () => {
    isEditDialogOpen.value = false;
    selectedUser.value = undefined;
};

const onRemoveUser = (user: UserWithRole) => {
    userPendingRemoval.value = user;
    isRemoveDialogOpen.value = true;
};

// ── User operations ────────────────────────────────────────────────────────

const confirmRemoveUser = async () => {
    if (!userPendingRemoval.value || !props.project?.id) return;
    isRemoving.value = true;
    try {
        const success = await aiiApiDelete(
            `projects/${props.project.id}/user/${userPendingRemoval.value.id}/rolemapping`
        );
        if (success) {
            // Optimistically remove user from the list
            users.value = users.value.filter(u => u.id !== userPendingRemoval.value!.id);
            isRemoveDialogOpen.value = false;
            userPendingRemoval.value = undefined;
        }
    } catch (error) {
        console.error('Failed to remove user:', error);
    } finally {
        isRemoving.value = false;
    }
};

const onUserOperationSuccess = async () => {
    isAddDialogOpen.value = false;
    closeEditDialog();
};

const onUsersAdded = (addedUsers: UserItem[]) => {
    // Add new users to the list with their assigned role
    users.value.push(...addedUsers);
};

const onUsersAddFailed = (failedUserIds: string[]) => {
    // Remove failed users from the list
    users.value = users.value.filter(u => !failedUserIds.includes(u.id));
};

const onRoleUpdated = (roleName: string) => {
    // Optimistically update the specific user's role immediately
    if (selectedUser.value) {
        selectedUser.value.role = { name: roleName } as UserRole;
    }
};

const onRoleUpdateFailed = (rollback: () => void) => {
    // Revert the optimistic update on failure
    rollback();
};

// ── Data fetching ──────────────────────────────────────────────────────────

const loadProjectUsers = async (options: { showLoading?: boolean } = {}) => {
    if (!props.project?.id) return;
    if (options.showLoading !== false) {
        isLoadingUsers.value = true;
    }
    try {
        const fetchedUsers: UserItem[] = await aiiApiGet(`projects/${props.project.id}/users`);
        users.value = fetchedUsers ?? [];
        await Promise.all(
            users.value.map((user, index) => loadUserRole(user.id, index))
        );
    } catch (error) {
        console.error('Failed to load project users:', error);
    } finally {
        if (options.showLoading !== false) {
            isLoadingUsers.value = false;
        }
    }
};

const loadUserRole = async (userId: string, userIndex: number) => {
    if (!props.project?.id) return;
    try {
        const role: UserRole = await aiiApiGet(`projects/${props.project.id}/users/${userId}/roles`);
        if (users.value[userIndex]) users.value[userIndex].role = role;
    } catch (error) {
        console.error(`Failed to load role for user ${userId}:`, error);
    }
};
</script>
