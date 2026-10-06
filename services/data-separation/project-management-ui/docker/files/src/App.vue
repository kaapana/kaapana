<template>
  <v-app>
    <v-main>
      <router-view :key="viewKey" />
    </v-main>
  </v-app>
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue'
import { useShellSettings } from '@kaapana/base-ui'
import store from '@/common/store'
import { UserItem } from '@/common/types'
import { aiiApiGet } from '@/common/services'
import { usePermissionsStore } from '@/permissions/permissions.store'

const { viewKey } = useShellSettings()
const user = ref<UserItem | null>(null)

async function fetchCurrentUser() {
  try {
    const userResp = await aiiApiGet("users/current");

    store.updateUser(userResp);
    user.value = userResp;

    return userResp; // important!
  } catch (error) {
    console.error(error);
    throw error;
  }
}

const permissions = usePermissionsStore();

onMounted(async () => {
  const currentUser = await fetchCurrentUser();

  await permissions.loadUserRights(currentUser.id);
});

</script>

<style>
/* A readable maximum for the project tables; the container centres itself in
   the space beyond it. */
.pm-view {
  max-width: 1600px;
}

.pm-search {
  max-width: 420px;
}

.pm-pending {
  background-color: rgba(var(--v-theme-warning), 0.12);
}
</style>
