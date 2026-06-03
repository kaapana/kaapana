<template>
  <v-card rounded="lg">
    <v-card-title class="d-flex align-center ga-2 pa-6 pb-4">
      <v-icon color="primary">{{ isAddMode ? 'mdi-account-plus' : 'mdi-account-edit' }}</v-icon>
      <div class="flex-grow-1">
        <span class="text-h6 font-weight-bold">
          {{ isAddMode ? 'Add Users to Project' : `Change Role: @${userToEdit?.username}` }}
        </span>
        <div class="text-caption text-medium-emphasis">
          Project: <strong>{{ project?.name ?? 'Unknown project' }}</strong>
        </div>
      </div>
      <v-btn variant="text" icon="mdi-close" @click="emit('cancel')" />
    </v-card-title>

    <v-divider />

    <v-card-text class="pa-6">
      <!-- Add mode: user search -->
      <template v-if="isAddMode">
        <p class="text-body-2 text-medium-emphasis mb-4">
          Search for users by name, username, or email and select one or more to add.
        </p>

        <v-autocomplete
          v-model="selectedUserIds"
          :items="availableUsers"
          :loading="isLoadingAvailableUsers"
          item-value="id"
          item-title="username"
          label="Search and select users"
          placeholder="Type to search..."
          prepend-inner-icon="mdi-account-search-outline"
          multiple
          clearable
          variant="outlined"
          no-data-text="No users found"
          class="mb-4"
          :custom-filter="userSearchFilter"
        >
          <template #selection="{ item, select, toggle, selected }">
            <v-chip v-bind="{ ...$attrs, selected, select, toggle }" size="small" class="mr-1">
              <v-icon icon="mdi-account-circle" size="18" />
              <span class="ml-1" style="font-family: monospace">{{ item.raw.username }}</span>
            </v-chip>
          </template>
          <template #item="{ props, item }">
            <v-list-item v-bind="props" class="py-3">
              <template #prepend>
                <v-icon icon="mdi-account-circle" color="primary" />
              </template>
              <v-list-item-title>{{ item.raw.first_name }} {{ item.raw.last_name }}</v-list-item-title>
              <v-list-item-subtitle>
                <span class="text-primary" style="font-family: monospace">@{{ item.raw.username }}</span>
                <span v-if="item.raw.email" class="ml-2">{{ item.raw.email }}</span>
              </v-list-item-subtitle>
            </v-list-item>
          </template>
        </v-autocomplete>

        <p v-if="selectedUserIds.length > 0" class="text-body-2 text-medium-emphasis">
          <v-icon size="14" class="mr-1">mdi-information-outline</v-icon>
          {{ selectedUserIds.length }} user{{ selectedUserIds.length > 1 ? 's' : '' }} selected
        </p>
      </template>

      <!-- Role selector -->
      <p class="text-subtitle-2 font-weight-medium mb-2 mt-4">Project Role</p>
      <v-item-group v-model="selectedRole" mandatory class="d-flex flex-column ga-2">
        <v-item v-for="role in availableRoles" :key="role.value" :value="role.value" v-slot="{ isSelected, toggle }">
          <v-card :variant="isSelected ? 'tonal' : 'elevated'" :color="isSelected ? 'primary' : undefined" rounded="lg" class="cursor-pointer" @click="toggle">
            <v-card-text class="d-flex align-center ga-3 pa-4">
              <v-icon :color="isSelected ? 'primary' : 'medium-emphasis'" :icon="role.icon" size="28" />
              <div class="flex-grow-1">
                <div class="text-subtitle-2 font-weight-semibold">{{ role.label }}</div>
                <div class="text-body-2 text-medium-emphasis">{{ role.description }}</div>
              </div>
              <v-icon v-if="isSelected" color="primary">mdi-check-circle</v-icon>
            </v-card-text>
          </v-card>
        </v-item>
      </v-item-group>

      <v-alert v-if="validationError" type="error" variant="tonal" density="compact" class="mt-4">
        {{ validationError }}
      </v-alert>
    </v-card-text>

    <v-divider />

    <v-card-actions class="pa-4">
      <v-spacer />
      <v-btn variant="text" @click="emit('cancel')">Cancel</v-btn>
      <v-btn color="primary" variant="flat" :loading="isSubmitting" :disabled="!canSubmit" @click="onSubmit">
        {{ isAddMode ? `Add ${selectedUserIds.length > 1 ? selectedUserIds.length + ' Users' : 'User'}` : 'Save Changes' }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted } from 'vue';
import { UserItem, UserRole } from '@/common/types';
import { aiiApiGet, aiiApiPost, aiiApiPut } from '@/common/services';

interface ProjectRef { id?: string; name?: string; }

const props = defineProps<{
  project: ProjectRef | null;
  actionType: 'add' | 'update';
  existingUserIds?: string[];
  userToEdit?: UserItem & { role?: UserRole };
}>();

const emit = defineEmits<{
  (e: 'cancel'): void;
  (e: 'success'): void;
  (e: 'users-added', users: UserItem[]): void;
  (e: 'users-add-failed', userIds: string[]): void;
  (e: 'role-updated', roleName: string): void;
  (e: 'role-update-failed', rollback: () => void): void;
}>();

const availableRoles = [
  { value: 'principal-investigator', label: 'Principal Investigator', description: 'Full control over the project.', icon: 'mdi-shield-account' },
  { value: 'scientist', label: 'Scientist', description: 'Can use approved software and applications.', icon: 'mdi-flask-outline' },
];

const isSystemUser = (u: UserItem) => {
  const username = (u.username || '').toLowerCase();
  const lastName = (u.last_name || '').toLowerCase();
  return username === 'system' || lastName === 'system' || username.endsWith('-system-user');
};

const availableUsers = ref<UserItem[]>([]);
const selectedUserIds = ref<string[]>([]);
const selectedRole = ref<string>(props.userToEdit?.role?.name ?? 'scientist');
const isLoadingAvailableUsers = ref(false);
const isSubmitting = ref(false);
const validationError = ref('');

const isAddMode = computed(() => props.actionType === 'add');

const userSearchFilter = (_: string, query: string, item: { raw: UserItem }) => {
  const user = item.raw;
  const q = query.toLowerCase().trim();
  return [user.username, user.email, user.first_name, user.last_name, `${user.first_name} ${user.last_name}`]
    .filter(Boolean)
    .some(f => f.toLowerCase().includes(q));
};

const canSubmit = computed(() => selectedRole.value && (isAddMode.value ? selectedUserIds.value.length > 0 : true));

onMounted(async () => { if (isAddMode.value) await loadAvailableUsers(); });

const loadAvailableUsers = async () => {
  if (!props.project?.id) return;
  isLoadingAvailableUsers.value = true;
  try {
    const existingIds = new Set(props.existingUserIds ?? []);
    availableUsers.value = (await aiiApiGet('users')).filter((u: UserItem) => !existingIds.has(u.id) && !isSystemUser(u));
  } catch (error) {
    console.error('Failed to load users:', error);
  } finally {
    isLoadingAvailableUsers.value = false;
  }
};

const onSubmit = async () => {
  validationError.value = '';
  if (isAddMode.value && selectedUserIds.value.length === 0) { validationError.value = 'Please select at least one user.'; return; }
  if (!selectedRole.value) { validationError.value = 'Please select a role.'; return; }

  isSubmitting.value = true;
  try {
    if (isAddMode.value) {
      const addedUsers = await addUsersToProject();
      emit('users-added', addedUsers);
    } else {
      await updateUserRole();
      emit('role-updated', selectedRole.value);
    }
    emit('success');
  } catch (error) {
    console.error('Failed to save user assignment:', error);
    validationError.value = 'Something went wrong. Please try again.';
    if (!isAddMode.value && props.userToEdit?.role) {
      const previousRole = { ...props.userToEdit.role };
      emit('role-update-failed', () => { props.userToEdit!.role = previousRole; });
    } else if (isAddMode.value) {
      emit('users-add-failed', [...selectedUserIds.value]);
    }
  } finally {
    isSubmitting.value = false;
  }
};

const addUsersToProject = async (): Promise<UserItem[]> => {
  if (!props.project?.id) return [];
  const addedUsers = availableUsers.value.filter(u => selectedUserIds.value.includes(u.id)).map(u => ({ ...u, role: { name: selectedRole.value } as UserRole }));
  await Promise.all(selectedUserIds.value.map(userId => aiiApiPost(`projects/${props.project!.id}/role/${selectedRole.value}/user/${userId}`)));
  return addedUsers;
};

const updateUserRole = async () => {
  if (!props.project?.id || !props.userToEdit) return;
  await aiiApiPut(`projects/${props.project.id}/user/${props.userToEdit.id}/rolemapping`, { role_name: selectedRole.value });
};
</script>
