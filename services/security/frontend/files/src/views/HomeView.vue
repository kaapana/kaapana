<script setup lang="ts">
import { RouterLink } from "vue-router";
import Header from "@/components/Header.vue";
</script>

<template>
  <Header title="Overview"></Header>
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