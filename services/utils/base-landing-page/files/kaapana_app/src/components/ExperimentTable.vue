<template>
  <v-card>
    <v-card-title>
      <v-col cols="4">
        <p>Experiment Management System</p>
      </v-col>
      <v-col cols="4">
        <!-- LocalKaapanaInstance
          v-if="clientInstance"
          :instance="clientInstance"
          :remote="false"
          @refreshView="refreshClient()"
          @ei="editClientInstance"
        ></LocalKaapanaInstance -->
        <template>
          <v-menu offset-y bottom transition="scale-transition" close-on-click>
            <template v-slot:activator="{ on, attrs }">
              <v-btn 
                v-on="on" 
                v-bind="attrs" 
                color="primary" 
                class="mx-2" 
                dark 
                rounded 
                outlined
              > remote </v-btn>
            </template>
            <v-list dense>
              <v-list-item>
                <add-remote-instance :remote="true"></add-remote-instance>
              </v-list-item>
              <v-list-item>
                <view-remote-instances 
                  :clientinstance="clientInstance" 
                  :remote="true"
                ></view-remote-instances>
              </v-list-item>
              <v-list-item>
                <sync-remote-instances 
                  :clientinstance="clientInstance" 
                  :remote="true"
                ></sync-remote-instances>
              </v-list-item >
            </v-list>
          </v-menu>
        </template>
        <v-btn 
          v-if="!clientInstance" 
          color="primary" 
          @click.stop="clientDialog=true" 
          dark="dark"
        >Add client instance </v-btn>
      </v-col>
      <v-col cols="4">
        <v-text-field
          v-model="search"
          append-icon="mdi-magnify"
          label="Search for Experiment"
          single-line
          hide-details
          class="mx-4"
        ></v-text-field>
      </v-col>
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
      <template v-slot:item.status="{ item }">
        <v-chip
          v-for="state in getStatesColorMap(item)"
          :color="state.color"
          class="ma-1 my-chip"
          dense
          small
          outlined>{{ state.count }}
        </v-chip>
      </template>
      <template v-slot:item.actions="{ item }">
        <v-col v-if="item.kaapana_instance.instance_name == clientInstance.instance_name" >
          <v-tooltip bottom>
            <template v-slot:activator="{ on, attrs }">
              <v-btn 
                v-bind="attrs" 
                v-on="on" 
                @click='abortExperiment(item)' 
                small 
                icon
              >
                <v-icon color="primary" dark>mdi-stop-circle-outline</v-icon>
              </v-btn>
            </template>
            <span>abort experiment including all it's jobs</span>
          </v-tooltip>
          <v-tooltip bottom>
            <template v-slot:activator="{ on, attrs }">
              <v-btn 
                v-bind="attrs" 
                v-on="on" 
                @click='restartExperiment(item)' 
                small 
                icon
              >
                <v-icon color="primary" dark>mdi-rotate-left</v-icon>
              </v-btn>
            </template>
            <span>restart experiment including all it's jobs</span>
          </v-tooltip>
          <v-tooltip bottom>
            <template v-slot:activator="{ on, attrs }">
              <v-btn 
                v-bind="attrs" 
                v-on="on" 
                @click='deleteExperiment(item)' 
                small 
                icon
              >
                <v-icon color="primary" dark>mdi-trash-can-outline</v-icon>
              </v-btn>
            </template>
            <span>delete experiment including all it's jobs</span>
          </v-tooltip>
        </v-col>
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
          <job-table 
            v-if="jobsofExpandedExperiment" 
            :jobs="jobsofExpandedExperiment" 
            :remote="clientInstance.remote" 
            @refreshView="refreshClient()"
          ></job-table>
        </td>
      </template>
    </v-data-table>
  </v-card>
</template>

<script>

import kaapanaApiService from "@/common/kaapanaApi.service";

import KaapanaInstance  from "@/components/KaapanaInstance.vue";
import LocalKaapanaInstance from "@/components/LocalKaapanaInstance.vue";
import AddRemoteInstance from "@/components/AddRemoteInstance.vue";
import ViewRemoteInstances from "@/components/ViewRemoteInstances.vue";
import SyncRemoteInstances from "@/components/SyncRemoteInstances.vue";
import JobTable from "./JobTable.vue";

export default {
name: 'ExperimentTable',

components: {
  KaapanaInstance,
  LocalKaapanaInstance,
  AddRemoteInstance,
  ViewRemoteInstances,
  SyncRemoteInstances,
  JobTable,
},

data () {
  return {
    search: '',
    expanded: [],
    experimentHeaders: [
      {
        text: 'Experiment ID',
        align: 'start',
        value: 'exp_id',
      },
      { text: 'Experiment Name', value: 'experiment_name' },
      { text: 'Dataset Name', value: 'dataset_name' },
      { text: 'Created', value: 'time_created' },
      { text: 'Updated', value: 'time_updated' },
      { text: 'Username', value: 'username' },
      { text: 'Owner Instance', value: 'kaapana_instance.instance_name' },
      { text: 'Status', value: 'status', align: 'center'},
      { text: 'Actions', value: 'actions', sortable: false, filterable: false, align: 'center'},
    ],
    clientInstance: {},
    clientExperiments: {},
    clientJobs: [],
    expandedExperiment: '',
    jobsofExpandedExperiment: [],
    jobsofExperiments: [],
    states_jobsofExperiment: [],
    abortID: '',
    restartID: '',
    deleteID: '',
    hover: false,
    activateAddRemote: false,
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
  },
  allInstances: {
    type: Array,
    required: true,
  }
},

computed: {
  filteredExperiments() {  
    if (this.experiments !== null) {
      if (this.expandedExperiment) {
        this.getJobsOfExperiment(this.expandedExperiment.experiment_name)
      }
      return this.experiments
    }
  },
},

methods: {
  // General Methods
  refreshClient() {
    this.getClientInstance()
    this.getClientExperiments()
    this.getClientJobs()
  },
  expandRow(item) {
    if (item === this.expanded[0]) {
      // Clicked row is already expanded, so collapse it
      this.expanded = []
      this.expandedExperiment = ''
    } else {
      // Clicked row is not expanded, so expand it
      this.expanded = [item]
      this.expandedExperiment = item
      this.getJobsOfExperiment(this.expandedExperiment.experiment_name)
    }
  },
  getStatesColorMap(item) {
    const states = item.experiment_jobs.map(job => job.status)
    const colorMap = {
      'queued': 'grey',
      'scheduled': 'blue',
      'running': 'green',
      'finished': 'black',
      'failed': 'red'
    }
    return Object.entries(colorMap).map(([state, color]) => ({
      color: color,
      count: states.filter(_state => _state === state).length
    }))
  },
  editClientInstance(instance) {
    this.clientPost = instance
    this.clientPost.fernet_encrypted = false
    this.clientDialog = true
    this.clientUpdate = true
  },
  abortExperiment(item) {
      this.abortID = item.exp_id
      console.log("Abort Experiment:", this.abortID)
      this.abortClientExperimentAPI(this.abortID, 'abort')
  },
  restartExperiment(item) {
      this.restartID = item.exp_id
      console.log("Restart Experiment:", this.restartID)
      this.restartClientExperimentAPI(this.restartID, 'scheduled')
  },
  deleteExperiment(item) {
      this.deleteID = item.exp_id
      console.log("Delete Experiment:", this.deleteID, "Item:", item)
      this.deleteClientExperimentAPI(this.deleteID)
  },

  // API Calls
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
  getClientExperiments() {
    kaapanaApiService
      .federatedClientApiGet("/experiments",{
      limit: 100,
      }).then((response) => {
        this.clientExperiments = response.data;
        console.log("clientExperiments: ", this.clientExperiments)
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
      })
      .catch((err) => {
        console.log(err);
      });
  },
  getJobsOfExperiment(experiment_name) {
      kaapanaApiService
        .federatedClientApiGet("/jobs",{
          experiment_name: experiment_name,
          limit: 100,
        }).then((response) => {
          if (this.expanded.length > 0) {
            this.jobsofExpandedExperiment = response.data;
          } else {
            this.jobsofExperiments = response.data;
          }
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
      })
      .catch((err) => {
          console.log(err);
      })
  },
}
}
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped lang="scss">
  .my-chip {
    border-width: 3px;
  }
</style>
