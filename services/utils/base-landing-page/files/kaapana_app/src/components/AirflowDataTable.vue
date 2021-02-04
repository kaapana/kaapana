<template>
  <div>
    <v-container grid-list-lg text-left>
      <v-card>
        <v-col cols="12">
        <v-autocomplete
          v-model="values"
          :items="items"
          chips
          label="Solo"
          multiple
          @change="filterDags()"
        ></v-autocomplete>
        </v-col>
          <v-simple-table style="margin: 20px">
          <template v-slot:default>
            <thead>
              <tr>
                <th class="text-left">Dag ID</th>
                <th class="text-left">Last Run</th>
                <th>Dag Runs</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="dag in displayDags" :key="dag.dag_id">
                <td>
                  <a
                    v-bind:href="`/flow/admin/airflow/graph?dag_id=${
                      dag.dag_id
                    }&execution_date=${new Date(
                      dag.last_scheduler_run
                    ).toISOString()}`"
                    target="_blank"
                  >
                    {{ dag.dag_id }}
                  </a>
                </td>
                <td v-if="getLastDagRunOfDag(dag.dag_id)">
                  <v-list>
                    <v-list-group :value="false">
                      <template v-slot:activator>
                        <v-list-item-title>
                          {{ new Date (
                            getLastDagRunOfDag(dag.dag_id).execution_time
                            ).toGMTString() }}
                          <v-btn
                            v-if="
                              getLastDagRunOfDag(dag.dag_id).state == 'success'
                            "
                            class="ma-2"
                            style="margin-left: 3px"
                            color="success"
                            dark
                            icon
                            title="Successful"
                          >
                            <v-icon dark> mdi-checkbox-marked-circle </v-icon>
                          </v-btn>
                          <v-btn
                            v-if="
                              getLastDagRunOfDag(dag.dag_id).state == 'failed'
                            "
                            class="ma-2"
                            color="red"
                            dark
                            icon
                            title="Failed"
                          >
                            <v-icon dark> mdi-cancel </v-icon>
                          </v-btn>
                        </v-list-item-title>
                      </template>
                      <v-list-item>
                        <v-row>
                          <v-list-item-title>
                            <!--
                              :key is important for rerendering.
                              Rule: Every the value in :key changes,
                                    the element rerenders.
                            -->
                            <v-btn
                              :key="loader"
                              class="ma-2"
                              :loading="loaders[displayDags.indexOf(dag)]"
                              :disabled="loaders[displayDags.indexOf(dag)]"
                              icon
                              color="green"
                              title="Clear Dag Run."
                              @click="
                                loader = displayDags.indexOf(dag);
                                clearDagRun(
                                  dag.dag_id,
                                  getLastDagRunOfDag(dag.dag_id).execution_time
                                  );
                                "
                            >
                              <v-icon>mdi-cached</v-icon>
                              <template v-slot:loader>
                                <span class="custom-loader">
                                  <v-icon light>mdi-cached</v-icon>
                                </span>
                              </template>
                            </v-btn>
                            <a
                              v-if="
                                getLastDagRunOfDag(dag.dag_id).state == 'failed'
                              "
                              v-bind:href="`/flow/admin/airflow/log?task_id=${
                                getLastDagRunOfDag(dag.dag_id).failed_task_id
                              }&dag_id=${dag.dag_id}&execution_date=${encodeURIComponent(
                                  getLastDagRunOfDag(dag.dag_id).execution_time
                              )}&format=json`"
                              target="_blank"
                            >
                              <v-btn
                                class="ma-2"
                                outlined
                                x-small
                                fab
                                color="teal"
                                title="Get Log of Failed Dag Run."
                              >
                                <v-icon>mdi-format-list-bulleted-square</v-icon>
                              </v-btn>
                            </a>
                          </v-list-item-title>
                        </v-row>
                      </v-list-item>
                    </v-list-group>
                  </v-list>
                </td>
                <td v-else>
                  <span></span>
                </td>
                <td>
                  <a
                    v-bind:href="`/flow/admin/airflow/graph?dag_id=${
                      dag.dag_id
                    }&execution_date=${new Date(
                      dag.last_scheduler_run
                    ).toISOString()}`"
                    target="_blank"
                  >
                    <v-btn
                      color="success"
                      depressed
                      style="margin-right: 3px; padding: 17px"
                      small
                      icon
                      outlined
                      title="Succesful Dag Runs."
                    >
                      {{ countSuccesfulDagRuns(dag.dag_id) }}
                    </v-btn>
                  </a>
                  <a
                    v-bind:href="`/flow/admin/airflow/graph?dag_id=${
                      dag.dag_id
                    }&execution_date=${new Date(
                      dag.last_scheduler_run
                    ).toISOString()}`"
                    target="_blank"
                  >
                    <v-btn
                      color="error"
                      depressed
                      style="margin-left: 3px; padding: 17px"
                      small
                      icon
                      outlined
                      title="Failed Dag Runs."
                    >
                      {{ countFailedDagRuns(dag.dag_id) }}
                    </v-btn>
                  </a>
                </td>
              </tr>
            </tbody>
          </template>
        </v-simple-table>
      </v-card>
    </v-container>
  </div>
</template>

<script>
export default {
  mounted() {
    this.fetchDags();
    this.fetchDagRuns();
  },
  data() {
    return {
      displayDags: [],
      dags: [],
      dagRuns: [],
      items: ['own', 'service'], // Here you can add new categories for filtering.
      values: ['own'], // Those are the default categories which you want to show in the table.
      // Contains the index of which loader in loaders should be activated.
      loader: null,
      /*
      Contains a list of booleans, which are responsible
      for the animation of the buttons (are they active or not).
      */
      loaders: [],
    };
  },
  watch: {
    loader() {
      const l = this.loader;
      this.loaders[l] = true;

      setTimeout(() => {
        this.loaders[l] = false;
      }, 3000);

      this.loader = null;
    },
  },
  methods: {
    async fetchDags() {
      try {
        const res = await fetch('/flow/kaapana/api/getdags');
        const val = await res.json();
        this.dags = val;
        /*
        Those methods are necessary because it's important they get first executed,
        when all data are fetch. If they would be in mounted,
        there weren't data which they need for working.
        */
        this.filterDags();
        this.createLoader();
      } catch (e) {
        console.log(e);
      }
    },
    async fetchDagRuns() {
      try {
        const res = await fetch('/flow/kaapana/api/getdagruns');
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
    filterDags() {
      /* eslint no-plusplus: ["error", { "allowForLoopAfterthoughts": true }] */
      /* Simple iteration with forEach doesn't work,
         because function isn't able to iterate over directory. */
      // Is necessary so the displayDags will be empty if you update filter list in a session.
      this.displayDags = [];
      const dagKeys = Object.keys(this.dags);
      let j;
      let i;
      for (j = 0; j < this.values.length; j++) {
        for (i = 0; i < dagKeys.length; i++) {
          if (dagKeys[i].substring(0, 7) === this.values[j]) {
            this.displayDags.push(this.dags[dagKeys[i]]);
          } else if (
            dagKeys[i].substring(0, 7) !== this.values[j]
            && dagKeys[i].substring(0, 7) !== 'service'
            && this.values[j] !== 'service'
          ) {
            this.displayDags.push(this.dags[dagKeys[i]]);
          }
        }
      }
    },
    getLastDagRunOfDag(dagId) {
      let lastDagRuns = [];
      let lastDagRun;
      lastDagRuns = this.dagRuns.filter((dagRun) => dagRun.dag_id === dagId);
      if (!lastDagRuns) {
        lastDagRun = 'No match';
      } else {
        lastDagRun = lastDagRuns[lastDagRuns.length - 1];
      }
      return lastDagRun;
    },
    createLoader() {
      this.loaders = [];
      this.displayDags.forEach((dag) => {
        const newLoaderObject = false;
        this.loaders.push(newLoaderObject);
      });
    },
    async clearDagRun(dagId, executionTime) {
      try {
        console.log('Start');
        const requestOptions = {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            dag_id: dagId,
            execution_time: executionTime,
          }),
        };
        const response = await fetch(`/flow/kaapana/api/clear/${dagId}/${executionTime}`, requestOptions);
        console.log(response);
        console.log('End');
      } catch (e) {
        console.log('Failed');
        console.log(e);
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.custom-loader {
  animation: loader 1s infinite;
  display: flex;
}
@-moz-keyframes loader {
  from {
    transform: rotate(0);
  }
  to {
    transform: rotate(360deg);
  }
}
@-webkit-keyframes loader {
  from {
    transform: rotate(0);
  }
  to {
    transform: rotate(360deg);
  }
}
@-o-keyframes loader {
  from {
    transform: rotate(0);
  }
  to {
    transform: rotate(360deg);
  }
}
@keyframes loader {
  from {
    transform: rotate(0);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>