<script setup lang="ts">
import { RouterLink } from "vue-router";
import Header from "@/components/Header.vue";

import { useThemeStore } from "@/stores/theme";

const themeStore = useThemeStore();
</script>

<template>
  <Header title="Title test" v-bind:divider="true">
    <p>Darkmode activated: {{ themeStore.useDarkMode }}</p>
  </Header>
  <main>
    <RouterLink to="/wazuh">Wazuh</RouterLink>
    <RouterLink to="/stackrox">StackRox</RouterLink>
  </main>
</template>

<style scoped>
main {
  display: flex;
  flex-direction: column;
  
}
</style>