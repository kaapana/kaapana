<script setup lang="ts">
import { kaapanaIcons } from '@kaapana/base-ui'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
</script>

<template>
  <v-menu :close-on-content-click="false" location="bottom end">
    <template #activator="{ props }">
      <v-btn v-bind="props" icon variant="text" title="Account">
        <v-icon :icon="kaapanaIcons.account"></v-icon>
      </v-btn>
    </template>
    <v-card>
      <v-list>
        <v-list-item
          :prepend-icon="kaapanaIcons.account"
          :title="auth.user?.username"
          subtitle="Welcome back!"
        ></v-list-item>
      </v-list>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="flat" block @click="auth.requestLogout()">
          Log Out
          <v-icon end :icon="kaapanaIcons.logout"></v-icon>
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-menu>
</template>
