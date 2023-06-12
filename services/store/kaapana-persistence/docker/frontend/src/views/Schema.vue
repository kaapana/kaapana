<template>
  <v-expansion-panels>
    <v-expansion-panel v-for="schema_urn in schemas" :key="schema_urn">
      <v-expansion-panel-title>{{ schema_urn }}</v-expansion-panel-title>
      <v-expansion-panel-text
        ><SchemaJsonView :urn="schema_urn"></SchemaJsonView
      ></v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels>
</template>

<script lang="ts" setup>
import { ref, onMounted, computed } from "vue";
import { useSchemaStore } from "@/store/app";
import SchemaJsonView from "@/components/SchemaJsonView.vue";
const store = useSchemaStore();

const getSchemas = computed(() => {
  return store.getSchemaURNs;
});

const schemas = computed(() => {
  return store.schema_urns;
});

onMounted(() => {
  store.fetchSchemaURNs();
});
</script>
