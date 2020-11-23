<template>
  <b-container>
    <dataTable></dataTable>
    <!--<b-row align-v="center">
      <card v-for="job in displayJobs" :key="job.id" :name="job.name"></card>
    </b-row>-->
  </b-container>
  <!--<div class="home">
  </div>-->
</template>

<script lang="ts">
// import Card from '@/components/Card.vue';
import DataTable from '@/components/DataTable.vue';
import Vue from 'vue';

export default Vue.extend({
  name: 'Home',
  components: {
    // card: Card,
    dataTable: DataTable,
  },
  mounted() {
    this.fetchData();
  },
  data() {
    return {
      jobs: [],
      currentPage: 1,
      rows: 1,
      perPage: 3,
      displayJobs: [],
    };
  },
  methods: {
    async fetchData() {
      const res = await fetch('jobs.json');
      const val = await res.json();
      this.jobs = val;
      this.displayJobs = val.slice(0, 3);
      this.rows = this.jobs.length;
      console.log(val);
    },
    paginate(currentPage: number) {
      const start = (currentPage - 1) * this.perPage;
      this.displayJobs = this.jobs.slice(start, start + 3);
    },
  },
});
</script>

<style lang="stylus" scoped>

</style>
