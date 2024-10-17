<template>
  <v-app>
    <v-app-bar :elevation="2" color="primary" density="compact">
      <v-app-bar-title @click="$router.push('/')" style="cursor:pointer">Projects Management</v-app-bar-title>
      <v-spacer></v-spacer>
      <v-menu v-if="user" location="bottom">
        <template v-slot:activator="{ props }">
          <v-btn icon="mdi-account-circle" variant="text" v-bind="props"></v-btn>
        </template>

        <v-card class="mx-auto" min-width="344" elevated>
          <v-list>
            <v-list-item :title="store.state.user?.username"
              :subtitle="`${store.state.user?.first_name} ${store.state.user?.last_name}`">
              <template v-slot:prepend>
                <v-icon icon="mdi-account-circle" size="x-large"></v-icon>
              </template>
              <template v-slot:subtitle="{ subtitle }">
                <div v-html="subtitle"></div>
              </template>
              <!-- <template v-slot:append>
                <v-btn color="grey-lighten-1" icon="mdi-information" variant="text"></v-btn>
              </template> -->
            </v-list-item>
          </v-list>
          <v-divider></v-divider>
        </v-card>
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
