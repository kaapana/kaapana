<template>
  <v-card
    :title="isAddMode ? 'Add Users to Project' : `Change Role: @${userToEdit?.username}`"
    :subtitle="`Project: ${project?.name ?? 'Unknown project'}`"
  >
    <v-card-text>
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
          :prepend-inner-icon="projectIcons.searchUser"
          multiple
          clearable
          no-data-text="No users found"
          class="mb-4"
          :custom-filter="userSearchFilter"
        >
          <template #selection="{ item }">
            <v-chip size="small" class="mr-1">
              <v-icon :icon="kaapanaIcons.account" size="18" />
              <span class="ml-1">{{ item.raw.username }}</span>
            </v-chip>
          </template>
          <template #item="{ props, item }">
            <v-list-item v-bind="props" class="py-3">
              <template #prepend>
                <v-icon :icon="kaapanaIcons.account" color="primary" />
              </template>
              <v-list-item-title>{{ item.raw.first_name }} {{ item.raw.last_name }}</v-list-item-title>
              <v-list-item-subtitle>
                <span class="text-primary">@{{ item.raw.username }}</span>
                <span v-if="item.raw.email" class="ml-2">{{ item.raw.email }}</span>
              </v-list-item-subtitle>
            </v-list-item>
          </template>
        </v-autocomplete>

        <v-btn
          v-if="isAdmin"
          size="x-small"
          variant="text"
          :color="showSystemUsers ? 'warning' : 'medium-emphasis'"
          :prepend-icon="projectIcons.systemUsers"
          class="mb-2"
          @click="showSystemUsers = !showSystemUsers; loadAvailableUsers()"
        >
          {{ showSystemUsers ? 'Hide System Users' : 'Show System Users' }}
        </v-btn>

        <p v-if="selectedUserIds.length > 0" class="text-body-2 text-medium-emphasis">
          <v-icon size="14" class="mr-1" :icon="kaapanaIcons.info" />
          {{ selectedUserIds.length }} user{{ selectedUserIds.length > 1 ? 's' : '' }} selected
        </p>
      </template>

      <!-- Role selector -->
      <p class="text-subtitle-2 font-weight-medium mb-2 mt-4">Project Role</p>
      <v-item-group v-model="selectedRole" mandatory class="d-flex flex-column ga-2">
        <v-item v-for="role in availableRoles" :key="role.name" :value="role.name" v-slot="{ isSelected, toggle }">
          <v-card
            :variant="isSelected ? 'tonal' : 'outlined'"
            :color="isSelected ? 'primary' : undefined"
            class="cursor-pointer"
            @click="toggle"
          >
            <v-card-text class="d-flex align-center ga-3 pa-4">
              <v-icon :color="isSelected ? 'primary' : 'medium-emphasis'" :icon="roleIcon(role.name)" size="28" />
              <div class="flex-grow-1">
                <div class="text-subtitle-2 font-weight-medium">{{ role.name }}</div>
                <div class="text-body-2 text-medium-emphasis">{{ role.description }}</div>
              </div>
              <v-icon v-if="isSelected" color="primary" :icon="kaapanaIcons.success" />
            </v-card-text>
          </v-card>
        </v-item>
      </v-item-group>

      <v-alert v-if="validationError" type="error" variant="tonal" density="compact" class="mt-4">
        {{ validationError }}
      </v-alert>
      <FailureAlert
        v-if="failure"
        :title="failure.title"
        :text="failure.text"
        :error="failure.error"
        :retry="failure.retry"
      />
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn :disabled="isSubmitting" @click="emit('cancel')">Cancel</v-btn>
      <v-btn color="primary" :loading="isSubmitting" :disabled="!canSubmit" @click="onSubmit">
        {{ isAddMode ? `Add ${selectedUserIds.length > 1 ? selectedUserIds.length + ' Users' : 'User'}` : 'Save Changes' }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script lang="ts" setup>
import FailureAlert from '@/components/FailureAlert.vue'
import { notify } from '@kyvg/vue3-notification'
import { kaapanaIcons, projectIcons, roleIcons } from '@/utils/projectIcons'
import { ref, computed, onMounted } from 'vue'
import { UserItem, UserRole } from '@/common/types'
import { aiiApiGet, aiiApiPost, aiiApiPut } from '@/common/services'
import { isAdminUser, isSystemUser, waitForStoreUser } from '@/common/userAccess'

interface Role { id: number; name: string; description: string; }

const roleIcon = (name: string) => roleIcons[name] ?? kaapanaIcons.account

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
}>();

const availableRoles = ref<Role[]>([]);

const isAdmin = ref(false);
const showSystemUsers = ref(false);

const availableUsers = ref<UserItem[]>([])
const selectedUserIds = ref<string[]>([])
const selectedRole = ref<string>(props.userToEdit?.role?.name ?? 'scientist')
const isLoadingAvailableUsers = ref(false)
const isSubmitting = ref(false)
const validationError = ref('')
const failure = ref<{ title: string; text: string; error: unknown; retry?: () => unknown } | null>(
  null,
)

const isAddMode = computed(() => props.actionType === 'add');

const userSearchFilter = (_: string, query: string, item?: { raw: UserItem }) => {
  if (!item) return false
  const user = item.raw
  const q = query.toLowerCase().trim()
  return [
    user.username,
    user.email,
    user.first_name,
    user.last_name,
    `${user.first_name} ${user.last_name}`,
  ]
    .filter(Boolean)
    .some(f => f.toLowerCase().includes(q));
};

const canSubmit = computed(() => selectedRole.value && (isAddMode.value ? selectedUserIds.value.length > 0 : true));

onMounted(async () => {
  waitForStoreUser(user => { isAdmin.value = isAdminUser(user); });
  await loadOptions();
});

const loadOptions = async () => {
  failure.value = null
  await loadRoles()
  if (isAddMode.value) await loadAvailableUsers()
}

const loadRoles = async () => {
  try {
    availableRoles.value = await aiiApiGet('projects/roles');
  } catch (error) {
    failure.value = {
      title: 'Roles not loaded',
      text: 'Could not load the project roles.',
      error,
      retry: loadOptions,
    }
  }
};

const loadAvailableUsers = async () => {
  if (!props.project?.id) return;
  isLoadingAvailableUsers.value = true;
  try {
    const existingIds = new Set(props.existingUserIds ?? []);
    availableUsers.value = (await aiiApiGet('users')).filter((u: UserItem) => !existingIds.has(u.id) && (showSystemUsers.value || !isSystemUser(u)));
  } catch (error) {
    failure.value = {
      title: 'Users not loaded',
      text: 'Could not load the users who can be added.',
      error,
      retry: loadOptions,
    }
  } finally {
    isLoadingAvailableUsers.value = false;
  }
};

const onSubmit = async () => {
  validationError.value = ''
  failure.value = null
  if (isAddMode.value && selectedUserIds.value.length === 0) {
    validationError.value = 'Please select at least one user.'
    return
  }
  if (!selectedRole.value) {
    validationError.value = 'Please select a role.'
    return
  }

  isSubmitting.value = true;
  try {
    if (isAddMode.value) {
      await addUsersToProject()
      const added = selectedUserIds.value.length
      notify({
        type: 'success',
        text: `${added} user${added !== 1 ? 's' : ''} added as "${selectedRole.value}". Access starts within a few minutes.`,
      })
    } else {
      await updateUserRole()
      notify({
        type: 'success',
        text: `@${props.userToEdit?.username} is now "${selectedRole.value}". The change applies within a few minutes.`,
      })
    }
    emit('success');
  } catch (error) {
    failure.value = isAddMode.value
      ? {
          title: 'Users not added',
          text: 'Not every selected user could be added to the project.',
          error,
        }
      : { title: 'Role not changed', text: 'Could not change the role.', error }
  } finally {
    isSubmitting.value = false;
  }
};

const addUsersToProject = async () => {
  if (!props.project?.id) return
  await Promise.all(
    selectedUserIds.value.map((userId) =>
      aiiApiPost(`projects/${props.project!.id}/role/${selectedRole.value}/user/${userId}`),
    ),
  )
}

const updateUserRole = async () => {
  if (!props.project?.id || !props.userToEdit) return;
  await aiiApiPut(`projects/${props.project.id}/user/${props.userToEdit.id}/rolemapping`, { role_name: selectedRole.value });
};
</script>
