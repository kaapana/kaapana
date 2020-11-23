<template>
  <div>
    <b-button v-b-toggle.collapse-3 class="m-1">Service Dags</b-button>
    <b-collapse id="collapse-3">
      <b-table-simple>
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
        <b-tbody v-for="dag in serviceDags" :key="dag.dag_id">
          <b-tr v-if="dag.dag_id.substr(0, 7) === 'service'">
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
        </b-tbody>
      </b-table-simple>
    </b-collapse>
  </div>
</template>

<script>
import Vue from 'vue';

export default Vue.extend({
  props: ['serviceDags', 'dagRuns'],
  methods: {
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
  },
});
</script>
