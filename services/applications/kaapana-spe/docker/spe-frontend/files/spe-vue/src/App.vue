<template>
  <v-app>
    <v-app-bar app color="primary" dark>
      <v-toolbar-title>Script Access Application</v-toolbar-title>
    </v-app-bar>
    <v-main>
      <router-view></router-view>
    </v-main>
    <v-footer app>
      <v-col class="text-center">© 2024 My Application</v-col>
    </v-footer>
  </v-app>
</template>

<script>
export default {
  name: 'App',
};
</script>

<style>
/* Add any global styles here */
</style>
