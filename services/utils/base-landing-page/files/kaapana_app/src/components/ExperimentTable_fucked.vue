<!-- eslint-disable vue/no-unused-vars -->
<template>
    <v-data-table
      :headers='headers'
      :items='filteredExperiments'
      :single-expand="singleExpand"
      :expanded.sync="expanded"
      item-key="name"
      show-expand
      class="elevation-1"
    >
      <template v-slot:top>
        <v-toolbar flat>
          <v-toolbar-title> <h3>Experiments</h3> </v-toolbar-title>
          <v-spacer></v-spacer>
          <v-switch
            v-model="singleExpand"
            label="Single expand"
            class="mt-2"
          ></v-switch>
        </v-toolbar>
      </template>
      <template v-slot:expanded-item="{ headers, item }">
        <td :colspan="headers.length">
          Hello World
          <job-table v-if="clientInstance" :jobs="clientJobs" :remote="clientInstance.remote" @refreshView="refreshClient()"></job-table>
        </td>
      </template>
    </v-data-table>
</template>

<script>

import kaapanaApiService from "@/common/kaapanaApi.service";
import JobTable from "./JobTable.vue";

export default {
    name: 'ExperimentTable',
    components: {
      JobTable,
    },
    data () {
      return {
        expanded: [], // ?
        singleExpand: false,  // ?
        clientInstance: {},
        clientJobs: [],
        search: "",
      }
    },
    props: {
        experiments: {
          type: Array,
          required: true
        },
        remote: {
          type: Boolean,
          default: true
        }
    },
    computed: {
        // expanded: [],
        // singleExpand: false,
        filteredExperiments() {
          if (this.experiments !== null) {
            // console.log(this.experiments)
            return this.experiments;
          } else {
            return [];
          }
        },
        headers() {
          let headers = []
          headers.push({
            text: 'Experiment name',
            value: 'experiment_name'
          })
          headers.push({
            text: 'Cohort name',
            value: 'cohort_name'
          })
          headers.push({
            text: 'Created',
            value: 'time_created'
          })
          headers.push({
            text: 'Updated',
            value: 'time_updated'
          })
          headers.push({
            text: 'Username',
            value: 'username'
          })  
          headers.push({
            text: 'Executing Instance Name',
            value: 'kaapana_instance.instance_name'
          })
          headers.push(
            { text: 'Actions', value: 'actions', sortable: false },
          ) 
          return headers
        }
    },  
    methods: {
        refreshClient() {
          this.getClientInstance()
          this.getClientJobs()
        },
        getClientInstance() {
          kaapanaApiService
            .federatedClientApiGet("/client-kaapana-instance")
            .then((response) => {
              this.clientInstance = response.data;
            })
            .catch((err) => {
              this.clientInstance = {}
            });
        },
        getClientJobs() {
          kaapanaApiService
            .federatedClientApiGet("/jobs",{
            limit: 100,
            }).then((response) => {
              this.clientJobs = response.data;
              console.log(this.clientJobs)
            })
            .catch((err) => {
              console.log(err);
            });
        },
      },
    }
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped lang="scss">

</style>
