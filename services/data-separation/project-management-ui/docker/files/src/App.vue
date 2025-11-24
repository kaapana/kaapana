<template>
  <v-app>
    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue'
import store from '@/common/store';
import { UserItem } from '@/common/types';
import { aiiApiGet } from '@/common/aiiApi.service';
import { usePermissionsStore } from '@/permissions/permissions.store';

const user = ref<UserItem | null>(null);


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
