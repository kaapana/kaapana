<template>
    <v-card>
      <v-card-title>
        <v-row>
            <h2>Experiments</h2>
        </v-row>
        <v-text-field
          v-model="search"
          append-icon="mdi-magnify"
          label="Search for Experiment"
          single-line
          hide-details
          class="mx-4"
        ></v-text-field>
      </v-card-title>
      <v-data-table
        :headers="experimentHeaders"
        :items="filteredExperiments"
        item-key="experiment_name"
        class="elevation-1"
        :search="search"
        :expanded="expanded"
        @click:row="expandRow"
      >
        <template v-slot:item.actions="{ item }">
          <v-menu transition="scale-transition"  v-if="item.kaapana_instance.instance_name == clientInstance.instance_name">
            <template v-slot:activator="{ on, attrs }">
              <v-btn color="primary" dark v-bind="attrs" v-on="on" >
                Action
              </v-btn>
            </template>
            <v-list>
              <v-list-item @click='abortExperiment(item)' >
                <v-list-item-title>Abort</v-list-item-title>
              </v-list-item>
              <v-list-item @click='restartExperiment(item)' >
                <v-list-item-title>Restart</v-list-item-title>
              </v-list-item>
              <v-list-item @click='deleteExperiment(item)'>
                <v-list-item-title>Delete</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
          <div v-else>
            <v-tooltip bottom>
              <template v-slot:activator="{ on, attrs }">
                <v-icon color="primary" dark v-bind="attrs" v-on="on">
                  mdi-cloud-braces
                </v-icon>
              </template>
              <span>No actions for REMOTE experiments!</span>
            </v-tooltip>
          </div>
        </template>
        <template #expanded-item="{headers,item}">
          <td :colspan="headers.length">
            <job-table v-if="jobsofExperiment" :jobs="jobsofExperiment" :remote="clientInstance.remote" @refreshView="refreshClient()"></job-table>
          </td>
        </template>
      </v-data-table>
    </v-card>
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
      search: '',
      expanded: [],
      experimentHeaders: [
        {
          text: 'Experiment Name',
          align: 'start',
          value: 'experiment_name',
        },
        { text: 'Cohort Name', value: 'cohort_name' },
        { text: 'Created', value: 'time_created' },
        { text: 'Updated', value: 'time_updated' },
        { text: 'Username', value: 'username' },
        { text: 'Owner Instance', value: 'kaapana_instance.instance_name' },
        { text: 'Actions', value: 'actions', sortable: false, filterable: false, align: 'center'},
      ],
      clientInstance: {},
      clientExperiments: {},
      clientJobs: [],
      expandedExperiment: '',
      jobsofExperiment: [],
      abortID: '',
      restartID: '',
      deleteID: '',
      hover: false,
    }
  },

  mounted () {
    this.refreshClient();
  },

  props: {
    instance: {
      type: Object,
      required: true
    },
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
    filteredExperiments() {
      if (this.experiments !== null) {
        console.log("filteredExperiments: ", this.experiments, "expandedExperiment", this.expandedExperiment)
        if (this.expandedExperiment !== null) {
          this.getJobsOfExperiment(this.expandedExperiment.experiment_name)
        }
        return this.experiments;
      } else {
        return [];
      }
    },
  },

  methods: {
    // General Methods
    refreshClient() {
      // console.log("refreshClient() in ExpeimentTable.vue")
      // this.getExpandedExperiment()
      this.getClientInstance()
      this.getClientExperiments()
      this.getClientJobs()
      // this.getJobsOfExpandedExperiment()
    },
    expandRow(item) {
        this.expanded = item === this.expanded[0] ? [] : [item]
        // console.log("In method expandRow: item", item, "this.expanded", this.expanded)
        this.expandedExperiment = item
        this.getJobsOfExperiment(this.expandedExperiment.experiment_name)
    },
    abortExperiment(item) {
        this.abortID = item.id
        console.log("Abort Experiment:", this.abortID)
        this.abortClientExperimentAPI(this.abortID, 'abort')
    },
    restartExperiment(item) {
        this.restartID = item.id
        console.log("Restart Experiment:", this.restartID)
        this.restartClientExperimentAPI(this.restartID, 'scheduled')
    },
    deleteExperiment(item) {
        this.deleteID = item.id
        console.log("Delete Experiment:", this.deleteID, "Item:", item)
        this.deleteClientExperimentAPI(this.deleteID)
    },

    // API Calls
    getClientInstance() {
      kaapanaApiService
        .federatedClientApiGet("/client-kaapana-instance")
        .then((response) => {
          this.clientInstance = response.data;
          // console.log("Client Instance in ExperimentTable", this.clientInstance)
        })
        .catch((err) => {
          this.clientInstance = {}
        });
    },
    getClientExperiments() {
      kaapanaApiService
        .federatedClientApiGet("/experiments",{
        limit: 100,
        }).then((response) => {
          this.clientExperiments = response.data;
          // console.log(this.clientExperiments)
        })
        .catch((err) => {
          console.log(err);
        });
    },
    getClientJobs() {
      kaapanaApiService
        .federatedClientApiGet("/jobs",{
          limit: 100,
        }).then((response) => {
          this.clientJobs = response.data;
          // console.log("Client Jobs in ExperimentTable", this.clientJobs)
        })
        .catch((err) => {
          console.log(err);
        });
    },
    getJobsOfExperiment(experiment_name) {
        kaapanaApiService
          .federatedClientApiGet("/experiment_jobs",{
            experiment_name: experiment_name,
            limit: 100,
          }).then((response) => {
            this.jobsofExperiment = response.data;
            console.log("Get Jobs of Experiment", this.jobsofExperiment)
          })
          .catch((err) => {
            console.log(err);
          })
    },
    deleteClientExperimentAPI(experiment_id) {
        kaapanaApiService
        .federatedClientApiDelete("/experiment",{
            experiment_id,
        }).then((response) => {
            console.log("Experiment deleted")
        })
        .catch((err) => {
            console.log(err);
        })
    },
    restartClientExperimentAPI(experiment_id, experiment_status) {
        kaapanaApiService
        .federatedClientApiPut("/experiment",{
            experiment_id,
            experiment_status,
        }).then((response) => {
            console.log("Experiment restarted")
        })
        .catch((err) => {
            console.log(err);
        })
    },
    abortClientExperimentAPI(experiment_id, experiment_status) {
        kaapanaApiService
        .federatedClientApiPut("/experiment",{
            experiment_id,
            experiment_status,
        }).then((response) => {
            console.log("Experiment restarted")
        })
        .catch((err) => {
            console.log(err);
        })
    },
  }
}
</script>