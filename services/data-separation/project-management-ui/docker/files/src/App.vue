<template>
  <v-app>
    <notifications
      position="bottom right"
      width="20%"
      :duration="5000"
      close-on-click
      @click="onNotificationClick"
    />
    <v-main>
      <router-view :key="viewKey" />
    </v-main>
    <ErrorDetailsDialog
      v-model="failureDetails.open"
      :title="failureDetails.current?.title"
      :text="failureDetails.current?.text"
      :error="failureDetails.current?.error ?? null"
    />
  </v-app>
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue'
import { ErrorDetailsDialog, useShellSettings } from '@kaapana/base-ui'
import { useFailureDetailsStore } from '@/stores/failureDetails'
import store from '@/common/store'
import { UserItem } from '@/common/types'
import { aiiApiGet } from '@/common/services'
import { usePermissionsStore } from '@/permissions/permissions.store'

const { viewKey } = useShellSettings()
const failureDetails = useFailureDetailsStore()

// A failure notification carries its details in `data.failure` (see
// utils/notifyFailure.ts); selecting it opens ErrorDetailsDialog.
function onNotificationClick(item: { data?: unknown }) {
  const failure = (item.data as { failure?: unknown } | undefined)?.failure
  if (failure) failureDetails.show(failure as never)
}
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
