<template>
  <v-app>
    <v-app-bar :elevation="2" color="primary" density="compact">
      <v-app-bar-title @click="$router.push('/')" style="cursor:pointer">Projects Management</v-app-bar-title>
      <v-spacer></v-spacer>
      <v-menu v-if="user">
        <template v-slot:activator="{ props }">
          <v-btn icon="mdi-account-circle" variant="text" v-bind="props"></v-btn>
        </template>

        <v-list>
          <v-list-item>
            <v-list-item-title>@{{ user.username }}</v-list-item-title>
          </v-list-item>
          <v-list-item>
            <v-list-item-title>{{ user.first_name }} {{ user.last_name }}</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </v-app-bar>
    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>

<script lang="ts" setup>
import { ref } from 'vue'
// import { onMounted } from "vue";
import store from '@/common/store';
import { UserItem } from '@/common/types';
import { aiiApiGet } from '@/common/aiiApi.service';


const user = ref<UserItem | null>(null);

// onMounted(() => {
//   console.log('mounted');
// });

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
