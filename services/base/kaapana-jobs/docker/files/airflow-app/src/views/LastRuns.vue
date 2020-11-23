<template>
  <b-container>
    <b-row align-v="center">
      <div>
        <b-table-simple class="table table-dark">
        <b-thead>
            <b-th>State</b-th>
            <b-th>Dag_Id</b-th>
            <b-th>Execution Date</b-th>
            <b-th>Run ID</b-th>
            <b-th>External Trigger</b-th>
        </b-thead>
        <b-thead>
            <b-tr v-for="filteredDagRun in filteredDagRuns" :key="filteredDagRun.dag_id">
                <td v-if="filteredDagRun.state === 'failed'">
                <b-button disabled variant="outline-danger">{{ filteredDagRun.state }}</b-button>
                </td>
                <td v-else-if="filteredDagRun.state === 'success'">
                <b-button disabled variant="outline-success">{{ filteredDagRun.state }}</b-button>
                </td>
                <td v-else></td>
                <td>{{ filteredDagRun.dag_id }}</td>
                <td>{{ filteredDagRun.execution_time }}</td>
                <td>{{ filteredDagRun.run_id }}</td>
                <td>True</td>
            </b-tr>
        </b-thead>
        </b-table-simple>
      </div>
    </b-row>
    <b-row align-v="center">
        <b-pagination
        v-model="currentPage"
        :total-rows="rows"
        :per-page="perPage"
        class="mt-4"
        @input="paginate(currentPage)"
    >
        <template #first-text><span class="text-success">First</span></template>
        <template #prev-text><span class="text-danger">Prev</span></template>
        <template #next-text><span class="text-warning">Next</span></template>
        <template #last-text><span class="text-info">Last</span></template>
        <template #ellipsis-text>
        <b-spinner small type="grow"></b-spinner>
        <b-spinner small type="grow"></b-spinner>
        <b-spinner small type="grow"></b-spinner>
        </template>
        <template #page="{ page, active }">
        <b v-if="active">{{ page }}</b>
        <i v-else>{{ page }}</i>
        </template>
        </b-pagination>
    </b-row>
  </b-container>
</template>

<script>
import Vue from 'vue';

export default Vue.extend({
  name: 'LastRun',
  components: {
  },
  mounted() {
    this.filterDagRunsAfterDagId();
  },
  data() {
    return {
      filteredDagRuns: [],
      currentPage: 1,
      rows: 1,
      perPage: 3,
      displayDagRuns: [],
    };
  },
  props: ['dagRuns', 'state', 'dagId'],
  methods: {
    filterDagRunsAfterDagId() {
      this.filteredDagRuns = this.dagRuns.filter((dagRun) => dagRun.state === this.state
      && dagRun.dag_id === this.dagId);
      return this.filterDagRunsAfterDagId;
    },
    paginate(currentPage) {
      const start = (currentPage - 1) * this.perPage;
      this.displayDagRuns = this.filteredDagRuns.slice(start, start + 3);
    },
  },
});
</script>

<style lang="scss" scoped>

</style>
