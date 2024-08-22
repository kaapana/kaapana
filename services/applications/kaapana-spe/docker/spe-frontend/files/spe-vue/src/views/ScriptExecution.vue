<!-- <template>
    <v-container>
      <v-select :items="availableScripts" v-model="selectedScript" label="Select Script"></v-select>
      <v-btn @click="runScript" color="primary">Run Script</v-btn>
      <v-alert v-if="result" type="success">Result: {{ result }}</v-alert>
    </v-container>
  </template>
  
  <script setup>
  import { ref } from 'vue';
  import { useMainStore } from '@/stores/main';
  
  const store = useMainStore();
  const selectedScript = ref(null);
  const result = ref('');
  
  const availableScripts = computed(() => {
    return store.scripts.filter(script => store.currentUser.access.includes(script.id));
  });
  
  const runScript = () => {
    if (selectedScript.value) {
      result.value = `Running ${selectedScript.value.name}...`;
      // Simulate script execution
      setTimeout(() => {
        result.value = `${selectedScript.value.name} completed successfully!`;
      }, 2000);
    }
  };
  </script>
   -->

  
<template>
  Hello World 2
</template>