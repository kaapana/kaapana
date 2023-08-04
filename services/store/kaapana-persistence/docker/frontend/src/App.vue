<template>
  <v-app>
    <v-tabs fixed-tabs>
      <!-- <v-tab to="/"><v-icon icon="mdi-home"></v-icon>home</v-tab> -->
      <v-tab to="/urn"
        ><!--<v-icon icon="mdi-feature-search-outline">--><v-icon
          icon="mdi-anchor"
        ></v-icon
        >URN</v-tab
      >
      <v-tab to="/schema"
        ><v-icon icon="mdi-table-multiple"></v-icon>Schemas</v-tab
      >
      <v-tab to="/object"
        ><v-icon icon="mdi-file-document-multiple"></v-icon>Objects</v-tab
      >
      <v-tab to="/cas"><v-icon icon="mdi-database"></v-icon>CAS</v-tab>
      <v-tab to="/api"><v-icon icon="mdi-code-brackets"></v-icon>API</v-tab>
    </v-tabs>
    <v-main>
      <router-view></router-view>
    </v-main>
  </v-app>
</template>

<script setup lang="ts"></script>
