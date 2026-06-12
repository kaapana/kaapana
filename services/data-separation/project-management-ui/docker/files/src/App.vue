<template>
  <v-app>
    <v-main :style="{ backgroundColor: contentBackground }">
      <router-view />
    </v-main>
  </v-app>
</template>

<script lang="ts" setup>
import { ref, onMounted, computed } from 'vue'
import store from '@/common/store';
import { UserItem } from '@/common/types';
import { aiiApiGet } from '@/common/services';
import { usePermissionsStore } from '@/permissions/permissions.store';
import { useTheme } from 'vuetify';

const user = ref<UserItem | null>(null);
const theme = useTheme();

const contentBackground = computed(() => {
  return theme.global.current.value.dark ? '#2a2a2a' : '#f5f5f5';
});


async function fetchCurrentUser() {
  store.state.fetching = true;

  try {
    const userResp = await aiiApiGet("users/current");

    store.updateUser(userResp);
    user.value = userResp;

    return userResp; // important!
  } catch (error) {
    console.error(error);
    throw error;
  } finally {
    store.state.fetching = false;
  }
}

const permissions = usePermissionsStore();

onMounted(async () => {
  const currentUser = await fetchCurrentUser();

  await permissions.loadUserRights(currentUser.id);
});

</script>
