<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
</script>

<template>
  <v-menu :close-on-content-click="false" location="bottom end">
    <template #activator="{ props }">
      <v-btn v-bind="props" icon variant="text" title="User">
        <v-icon>mdi-account-circle</v-icon>
      </v-btn>
    </template>
    <v-card>
      <v-list>
        <v-list-item prepend-icon="mdi-account-circle" :title="auth.user?.username" subtitle="Welcome back!"></v-list-item>
      </v-list>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="flat" block @click="auth.requestLogout()">
          Log Out
          <v-icon end>mdi-exit-to-app</v-icon>
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-menu>
</template>
