<!-- <template>
    <v-container>
      <v-form @submit.prevent="apply">
        <v-text-field v-model="name" label="Name" required></v-text-field>
        <v-text-field v-model="email" label="Email" required></v-text-field>
        <v-btn type="submit" color="primary">Apply for Access</v-btn>
      </v-form>
    </v-container>
  </template>
  
  <script setup>
  import { ref } from 'vue';
  import { useMainStore } from '@/stores/main';
  
  const store = useMainStore();
  const name = ref('');
  const email = ref('');
  
  const apply = () => {
    store.applyForAccess({ name: name.value, email: email.value });
    name.value = '';
    email.value = '';
  };
  </script>
   -->


<template>
  Hello World 3
</template>