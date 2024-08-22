<!-- <template>
  <v-container>
    <v-list>
      <v-list-item v-for="user in users" :key="user.id">
        <v-list-item-content>
          <v-list-item-title>{{ user.name }}</v-list-item-title>
          <v-list-item-subtitle>{{ user.email }}</v-list-item-subtitle>
        </v-list-item-content>
        <v-list-item-action v-if="user.status === 'pending'">
          <v-btn @click="approve(user.id)" color="success">Approve</v-btn>
        </v-list-item-action>
        <v-list-item-action v-else>
          <v-select :items="scripts" v-model="userScript" label="Grant Script Access"></v-select>
          <v-btn @click="grantAccess(user.id)" color="primary">Grant</v-btn>
        </v-list-item-action>
      </v-list-item>
    </v-list>
  </v-container>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useMainStore } from '@/stores/main';

const store = useMainStore();
const userScript = ref(null);

const users = computed(() => store.users);
const scripts = computed(() => store.scripts);

const approve = (userId) => {
  store.approveUser(userId);
};

const grantAccess = (userId) => {
  if (userScript.value) {
    store.grantAccess(userId, userScript.value);
  }
};
</script> -->

<template>
  Hello World
</template>