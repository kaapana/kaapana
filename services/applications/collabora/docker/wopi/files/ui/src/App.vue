<template>
  <v-app>
    <v-main>
      <Documents />
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
  import Documents from '@/components/Documents.vue'
  import { useTheme } from 'vuetify'
  const theme = useTheme()
  
  function applyTheme() {
    if("settings" in localStorage) {
      const settings = JSON.parse(localStorage["settings"]);
      theme.global.name.value = settings["darkMode"] ? 'dark' : 'light'
    }
  }

  onstorage = (event) => {
    if(event.key == "settings") {
      applyTheme()
    }
  }

  applyTheme()
</script>
