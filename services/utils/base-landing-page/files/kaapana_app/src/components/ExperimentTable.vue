<template>
  <v-card>
    <v-card-title>
      <v-col cols="4">
        <p class="mx-4 my-2">Experiment List</p>
      </v-col>
      <v-col cols="2">
        <!-- LocalKaapanaInstance
          v-if="clientInstance"
          :instance="clientInstance"
          :remote="false"
          @refreshView="refreshClient()"
          @ei="editClientInstance"
        ></LocalKaapanaInstance -->
        <!-- template>
          <v-menu offset-y bottom transition="scale-transition" close-on-click>
            <template v-slot:activator="{ on, attrs }">
              <v-btn v-on="on" v-bind="attrs" color="primary" class="mx-2" dark rounded outlined> remote </v-btn>
            </template>
            <v-list dense>
              <v-list-item>
                <add-remote-instance :remote="true"></add-remote-instance>
              </v-list-item>
              <v-list-item>
                <view-remote-instances :clientinstance="clientInstance" :remote="true"></view-remote-instances>
              </v-list-item>
              <v-list-item>
                <sync-remote-instances :clientinstance="clientInstance" :remote="true"></sync-remote-instances>
              </v-list-item >
            </v-list>
          </v-menu>
        </template -->
        <v-btn v-if="!clientInstance" color="primary" @click.stop="clientDialog=true" dark="dark">Add client instance </v-btn>
      </v-col>
      <v-col align="right">
        <v-tooltip bottom>
          <template v-slot:activator="{ on, attrs }">
            <v-btn v-on="on" @click='refreshClient()' small icon>
              <v-icon color="primary" large class="mx-2" dark>mdi-refresh</v-icon> 
            </v-btn> 
          </template>
          <span>refresh experiment list</span>
        </v-tooltip>
      </v-col>
      <v-col cols="4">
        <v-text-field
          v-model="search"
          append-icon="mdi-magnify"
          label="Search for Experiment"
          single-line
          hide-details
          class="mb-4"
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
          class="ml-1 my-chip"
          dense
          small
          outlined>{{ state.count }}
        </v-chip>
      </template>
      <template v-slot:item.actions="{ item }">
        <div v-if="!item.automatic_execution">
          <v-tooltip bottom>
            <template v-slot:activator="{ on, attrs }">
              <v-btn v-bind="attrs" v-on="on" @click='startExperimentManually(item)' small icon>
                <v-icon color="primary" dark>mdi-play-circle-outline</v-icon>
              </v-btn>
            </template>
            <span>start scheduled experiment manually</span>
          </v-tooltip>
        </div>
        <div v-else>
          <v-col v-if="item.kaapana_instance.instance_name == clientInstance.instance_name" >
            <v-tooltip bottom>
              <template v-slot:activator="{ on, attrs }">
                <v-btn v-bind="attrs" v-on="on" @click='abortExperiment(item)' small icon>
                  <v-icon color="primary" dark>mdi-stop-circle-outline</v-icon>
                </v-btn>
              </template>
              <span>abort experiment including all its jobs</span>
            </v-tooltip>
            <v-tooltip bottom>
              <template v-slot:activator="{ on, attrs }">
                <v-btn v-bind="attrs" v-on="on" @click='restartExperiment(item)' small icon>
                  <v-icon color="primary" dark>mdi-rotate-left</v-icon>
                </v-btn>
              </template>
              <span>restart experiment including all its jobs</span>
            </v-tooltip>
            <v-tooltip bottom>
              <template v-slot:activator="{ on, attrs }">
                <v-btn v-bind="attrs" v-on="on" @click='deleteExperiment(item)' small icon>
                  <v-icon color="primary" dark>mdi-trash-can-outline</v-icon>
                </v-btn>
              </template>
              <span>delete experiment including all its jobs</span>
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
        </div>
      </template>
      <template #expanded-item="{headers,item}">
        <td :colspan="headers.length">
          <job-table v-if="jobsofExpandedExperiment" :jobs="jobsofExpandedExperiment" :remote="clientInstance.remote" @refreshView="refreshClient()"></job-table>
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
      // { text: 'Auto', value: 'automatic_execution', sortable: false, filterable: false, align: 'center'}
    ],
    clientInstance: {},
    clientExperiments: {},
    clientJobs: [],
    expandedExperiment: '',
    jobsofExpandedExperiment: [],
    jobsofExperiments: [],
    states_jobsofExperiment: [],
    manual_startID: '',
    abortID: '',
    restartID: '',
    deleteID: '',
    hover: false,
    activateAddRemote: false,
    shouldExpand: true,
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
    if ( this.shouldExpand == true) {
      if (item === this.expanded[0] ) {
        // Clicked row is already expanded, so collapse it
        this.expanded = []
        this.expandedExperiment = ''
      } else {
        // Clicked row is not expanded, so expand it
        this.expanded = [item]
        this.expandedExperiment = item
        this.getJobsOfExperiment(this.expandedExperiment.experiment_name)
      }
    } else {
      this.shouldExpand = true
      }
  },
  getStatesColorMap(item) {
    const states = item.experiment_jobs.map(job => job.status)
    const colorMap = {
      'queued': 'grey',
      'scheduled': 'blue',
      'pending': 'orange',
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
  startExperimentManually(item) {
    this.shouldExpand = false
    this.manual_startID = item.exp_id,
    console.log("Manually start Experiment: ", this.manual_startID)
    this.manuallyStartClientExperimentAPI(this.manual_startID, 'confirmed')
  },
  abortExperiment(item) {
      this.shouldExpand = false
      this.abortID = item.exp_id
      console.log("Abort Experiment: ", this.abortID)
      this.abortClientExperimentAPI(this.abortID, 'abort')
  },
  restartExperiment(item) {
      this.shouldExpand = false
      this.restartID = item.exp_id
      console.log("Restart Experiment: ", this.restartID)
      this.restartClientExperimentAPI(this.restartID, 'scheduled')
  },
  deleteExperiment(item) {
      this.shouldExpand = false
      this.deleteID = item.exp_id
      console.log("Delete Experiment: ", this.deleteID, "Item:", item)
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
  deleteClientExperimentAPI(exp_id) {
      kaapanaApiService
      .federatedClientApiDelete("/experiment",{
          exp_id,
      }).then((response) => {
        // positive notification
        const message = `Successfully deleted experiment ${exp_id}`
        this.$notify({
          type: 'success',
          title: message,
        })
      })
      .catch((err) => {
        // negative notification
        const message = `Error while deleting experiment ${exp_id}`
        this.$notify({
          type: "error",
          title: message,
        })
        console.log(err);
      })
  },
  restartClientExperimentAPI(exp_id, experiment_status) {
      kaapanaApiService
      .federatedClientApiPut("/experiment",{
          exp_id,
          experiment_status,
      }).then((response) => {
        // positive notification
        const message = `Successfully restarted experiment ${exp_id}`
        this.$notify({
          type: "success",
          title: message,
        })
      })
      .catch((err) => {
        // negative notification
        const message = `Error while restarting experiment ${exp_id}`
        this.$notify({
          type: "error",
          title: message,
        })
          console.log(err);
      })
  },
  abortClientExperimentAPI(exp_id, experiment_status) {
      kaapanaApiService
      .federatedClientApiPut("/experiment",{
          exp_id,
          experiment_status,
      }).then((response) => {
        // positive notification
        const message = `Successfully aborted experiment ${exp_id}`
        this.$notify({
          type: "success",
          title: message,
        })
      })
      .catch((err) => {
        // negative notification
        const message = `Error while aborting experiment ${exp_id}`
        this.$notify({
          type: "error",
          title: message,
        })
        console.log(err);
      })
  },
  manuallyStartClientExperimentAPI(exp_id, experiment_status) {
      kaapanaApiService
        .federatedClientApiPut("/experiment",{
            exp_id,
            experiment_status,
        }).then((response) => {
          // positive notification
          const message = `Successfully manually started experiment ${exp_id}`
          this.$notify({
            type: "success",
            title: message,
          })
        })
        .catch((err) => {
          // negative notification
          const message = `Error while manually starting experiment ${exp_id}`
          this.$notify({
            type: "error",
            title: message,
          })
          console.log(err);
        })
    }
  }
}
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped lang="scss">
  .my-chip {
    border-width: 2px;
  }
</style>
