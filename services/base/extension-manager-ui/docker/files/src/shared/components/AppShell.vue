<script setup lang="ts">
import ToggleDarkMode from '@/shared/components/ToggleDarkMode.vue'
</script>

<template>
  <v-app-bar flat density="comfortable">
    <v-app-bar-title>
      <router-link to="/catalog" class="app-shell-title-link"> Extension Manager </router-link>
    </v-app-bar-title>

    <template #append
      ><!-- Right-aligns content inside the bar -->
      <v-btn variant="text" to="/catalog" exact>
        <v-icon start>mdi-package-variant</v-icon>
        Catalog
      </v-btn>
      <v-btn variant="text" to="/extensions">
        <v-icon start>mdi-database-cog</v-icon>
        Extensions
      </v-btn>
      <v-btn variant="text" to="/repositories">
        <v-icon start>mdi-source-branch</v-icon>
        Repositories
      </v-btn>
      <ToggleDarkMode />
    </template>
  </v-app-bar>

  <v-main> <slot /><!-- Filled by whichever view matches the current URL --> </v-main>
</template>

<style scoped>
.app-shell-title-link {
  color: inherit;
  text-decoration: none;
}
</style>
