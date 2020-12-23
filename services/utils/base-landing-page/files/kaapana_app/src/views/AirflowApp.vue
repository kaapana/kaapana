<template>
  <v-container>
    <dataTable></dataTable>
  </v-container>
</template>

<script lang="ts">
import DataTable from '@/components/AirflowDataTable.vue';
import Vue from 'vue';

export default Vue.extend({
  components: {
    dataTable: DataTable,
  },
});
</script>

<style lang="scss" scoped>
</style>