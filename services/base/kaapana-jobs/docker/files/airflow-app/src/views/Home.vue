<template>
  <v-container>
    <dataTable></dataTable>
  </v-container>
</template>

<script lang="ts">
import DataTable from '@/components/DataTable.vue';
import Vue from 'vue';

export default Vue.extend({
  name: 'Home',
  components: {
    dataTable: DataTable,
  },
});
</script>

<style lang="scss" scoped>
</style>
