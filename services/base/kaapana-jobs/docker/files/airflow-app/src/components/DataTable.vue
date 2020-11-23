<template>
  <div>
    <b-table-simple class="table table-dark">
        <b-thead>
          <b-th>
            <b-icon
              icon="info-circle"
              scale="1"
              variant="info"
              title="Use this toggle to pause a DAG.
                  The scheduler won't schedule new tasks instances
                  for a paused DAG. Tasks already running at pause time won't be affected."
            ></b-icon>
          </b-th>
          <b-th>Dag_Id</b-th>
          <b-th>
            Recent Tasks
            <b-icon
              icon="info-circle"
              scale="1"
              variant="info"
              title="Execution Date/Time of Highest Dag Run."
            ></b-icon>
          </b-th>
          <b-th>Last Run</b-th>
        </b-thead>
        <tbody>
          <b-tr v-for="dag in nonServiceDags" :key="dag.dag_id">
            <b-td>
              <b-form-checkbox
                switch
                :checked="dag.is_active"
              ></b-form-checkbox>
            </b-td>
            <b-td>{{ dag.dag_id }}</b-td>
            <b-td>{{ dag.last_scheduler_run }}</b-td>
            <b-td>
              <router-link
                v-if="countSuccesfulDagRuns(dag.dag_id) > 0"
                :to="{
                  name: 'LastRuns',
                  params: { dagRuns, state: 'success', dagId: dag.dag_id },
                }"
              >
                <b-button
                  pill
                  variant="outline-success"
                  style="margin-right: 3px"
                >
                  {{ countSuccesfulDagRuns(dag.dag_id) }}
                </b-button>
              </router-link>
              <b-button
                v-if="countSuccesfulDagRuns(dag.dag_id) == 0"
                disabled
                pill
                variant="outline-success"
                style="margin-right: 3px"
              >
                {{ countSuccesfulDagRuns(dag.dag_id) }}
              </b-button>
              <router-link
                v-if="countFailedDagRuns(dag.dag_id) > 0"
                :to="{
                  name: 'LastRuns',
                  params: { dagRuns, state: 'failed', dagId: dag.dag_id },
                }"
              >
                <b-button
                  pill
                  variant="outline-danger"
                  style="margin-left: 3px"
                >
                  {{ countFailedDagRuns(dag.dag_id) }}
                </b-button>
              </router-link>
              <b-button
                v-if="countFailedDagRuns(dag.dag_id) == 0"
                disabled
                pill
                variant="outline-danger"
                style="margin-left: 3px"
              >
                {{ countFailedDagRuns(dag.dag_id) }}
              </b-button>
            </b-td>
          </b-tr>
        </tbody>
      </b-table-simple>
    <serviceDagsTable :serviceDags="serviceDags" :dagRuns="dagRuns"></serviceDagsTable>
  </div>
</template>

<script>
import ServiceDagsTable from './ServiceDagsTable.vue';

export default {
  components: {
    serviceDagsTable: ServiceDagsTable,
  },
  mounted() {
    /* fetch('http://e230-pc07:8081/flow/kaapana/api/getdags')// + <domain> at the beginning
      .then((response) => response.json())
      .then((data) => {
        this.dags = data;
        console.log(data);
      });
   fetch('https://e230-pc07/flow/kaapana/api/getdags')// + <domain> at the beginning
      .then((response) => response.json())
      .then((data) => {
        this.dags = data;
        console.log(data);
      }); */
    this.fetchDags();
    this.fetchDagRuns();
    // this.filterAfterServiceDags();
  },
  data() {
    return {
      serviceDags: [],
      nonServiceDags: [],
      dags: [],
      dagRuns: [],
    };
  },
  methods: {
    async fetchDags() {
      try {
        const res = await fetch('getdags.json');
        const val = await res.json();
        this.dags = val;
        this.filterAfterServiceDags();
      } catch (e) {
        console.log(e);
      }
    },
    async fetchDagRuns() {
      try {
        const res = await fetch('getdagruns.json');
        const val = await res.json();
        this.dagRuns = val;
      } catch (e) {
        console.log(e);
      }
    },
    countSuccesfulDagRuns(dagId) {
      let equalDagRuns = [];
      equalDagRuns = this.dagRuns.filter(
        (dagRun) => dagRun.dag_id === dagId && dagRun.state === 'success',
      );
      return equalDagRuns.length;
    },
    countFailedDagRuns(dagId) {
      let equalDagRuns = [];
      equalDagRuns = this.dagRuns.filter(
        (dagRun) => dagRun.dag_id === dagId && dagRun.state === 'failed',
      );
      return equalDagRuns.length;
    },
    filterAfterServiceDags() {
      /* eslint no-plusplus: ["error", { "allowForLoopAfterthoughts": true }] */
      /* Simple iteration with forEach doesn't work,
         because function isn't able to iterate over directory. */
      const dagKeys = Object.keys(this.dags);
      let i;
      for (i = 0; i < dagKeys.length; i++) {
        if (dagKeys[i].substring(0, 7) === 'service') {
          this.serviceDags.push(this.dags[dagKeys[i]]);
        } else {
          this.nonServiceDags.push(this.dags[[dagKeys[i]]]);
        }
      }
    },
  },
};
</script>

<style lang="scss" scoped>
</style>
