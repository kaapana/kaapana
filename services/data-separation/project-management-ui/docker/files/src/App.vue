<template>
  <v-app>
    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>

<script lang="ts" setup>
import { ref } from 'vue'
import store from '@/common/store';
import { UserItem } from '@/common/types';
import { aiiApiGet } from '@/common/aiiApi.service';


const user = ref<UserItem | null>(null);


function fetchCurrentUser() {
  store.state.fetching = true;
  try {
    aiiApiGet('users/current').then((userResp: UserItem) => {
      store.updateUser(userResp);
      user.value = userResp
      store.state.fetching = false;
    });
  } catch (error: unknown) {
    console.log(error);
    store.state.fetching = false;
  }
}

fetchCurrentUser();

</script>
