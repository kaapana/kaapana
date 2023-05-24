<template>
  <v-card>
    <v-card-title>
      <v-col cols="4">
        <p class="mx-4 my-2">Workflow List</p>
      </v-col>
      <v-col cols="4" align="right">
        <v-tooltip bottom>
          <template v-slot:activator="{ on, attrs }">
            <v-btn class="pa-6" v-on="on" @click='checkForRemoteUpdates' small icon>
              <v-icon color="primary" large dark>
                mdi-sync
              </v-icon> 
            </v-btn> 
          </template>
          <span>sync manually with remote instances</span>
        </v-tooltip>
        <v-tooltip bottom>
          <template v-slot:activator="{ on, attrs }">
            <v-btn class="pa-6" v-on="on" @click='redirectToAirflow()' small icon>
              <v-icon color="primary" large dark>
                mdi-chart-timeline-variant
              </v-icon> 
            </v-btn> 
          </template>
          <span>redirect to Airflow worklfow engine</span>
        </v-tooltip>
        <v-tooltip bottom>
          <template v-slot:activator="{ on, attrs }">
            <v-btn class="pa-6" v-on="on" @click='refreshClient()' small icon>
              <v-icon color="primary" large  dark>mdi-refresh</v-icon> 
            </v-btn> 
          </template>
          <span>refresh workflow list</span>
        </v-tooltip>
      </v-col>
      <v-col cols="4">
        <v-text-field
          v-model="search"
          append-icon="mdi-magnify"
          label="Search for Workflow"
          single-line
          hide-details
          class="mb-4"
        ></v-text-field>
      </v-col>
    </v-card-title>
    <v-data-table
      :headers="workflowHeaders"
      :items="filteredWorkflows"
      item-key="workflow_name"
      class="elevation-1"
      :search="search"
      :expanded="expanded"
      @click:row="expandRow"
      :loading="loading"
      loading-text="Request is processed - wait a few seconds."
    >
      <template v-slot:item.time_created="{ item }">
        {{ new Date(item.time_created).toLocaleString() }}
      </template>
      <template v-slot:item.time_updated="{ item }">
        {{ new Date(item.time_updated).toLocaleString() }}
      </template>
      <template v-slot:item.status="{ item }">
        <v-btn
          v-for="state in getStatesColorMap(item, $vuetify.theme.dark)"
          :color="state.color"
          class="ml-1 my-chip"
          dense
          x-small
          rounded
          outlined
          @click="getJobsOfWorkflow(item.workflow_name, state.status, collapse=false)"
        >
          {{ state.count }}
        </v-btn>
      </template>
      <template v-slot:item.actions="{ item }">
        <div v-if="item.service_workflow">
          <v-tooltip bottom>
            <template v-slot:activator="{ on }">
              <v-icon v-on="on" color="primary" dark>mdi-account-hard-hat-outline</v-icon>
            </template>
            <span> No actions for service workflows! </span>
          </v-tooltip>
        </div>
        <div v-else-if="!item.automatic_execution">
          <v-tooltip bottom>
            <template v-slot:activator="{ on, attrs }">
              <v-btn v-bind="attrs" v-on="on" @click='startWorkflowManually(item)' small icon>
                <v-icon color="red" dark>mdi-play-circle-outline</v-icon>
              </v-btn>
            </template>
            <span>start scheduled workflow manually</span>
          </v-tooltip>
        </div>
        <div v-else>
          <v-col v-if="!item.kaapana_instance.remote" >
            <v-tooltip bottom>
              <template v-slot:activator="{ on, attrs }">
                <v-btn v-bind="attrs" v-on="on" @click='abortWorkflow(item)' small icon>
                  <v-icon color="primary" dark>mdi-stop-circle-outline</v-icon>
                </v-btn>
              </template>
              <span>abort workflow including all its jobs</span>
            </v-tooltip>
            <v-tooltip bottom>
              <template v-slot:activator="{ on, attrs }">
                <v-btn v-bind="attrs" v-on="on" @click='restartWorkflow(item)' small icon>
                  <v-icon color="primary" dark>mdi-rotate-left</v-icon>
                </v-btn>
              </template>
              <span>restart workflow including all its jobs</span>
            </v-tooltip>
            <v-tooltip bottom>
              <template v-slot:activator="{ on, attrs }">
                <v-btn v-bind="attrs" v-on="on" @click='deleteWorkflow(item)' small icon>
                  <v-icon color="primary" dark>mdi-trash-can-outline</v-icon>
                </v-btn>
              </template>
              <span>delete workflow including all its jobs</span>
            </v-tooltip>
          </v-col>
          <div v-else>
            <v-tooltip bottom>
              <template v-slot:activator="{ on, attrs }">
                <v-icon color="primary" dark v-bind="attrs" v-on="on">
                  mdi-cloud-braces
                </v-icon>
              </template>
              <span>No actions for REMOTE workflows!</span>
            </v-tooltip>
          </div>
        </div>
      </template>
      <template #expanded-item="{headers,item}">
        <td :colspan="headers.length">
          <job-table v-if="jobsofExpandedWorkflow" :jobs="jobsofExpandedWorkflow" @refreshView="refreshClient()"></job-table>
        </td>
      </template>
    </v-data-table>
  </v-card>
</template>

<script>

import kaapanaApiService from "@/common/kaapanaApi.service";
import JobTable from "./JobTable.vue";

export default {
name: 'WorkflowTable',

components: {
  JobTable,
},

data () {
  return {
    search: '',
    expanded: [],
    workflowHeaders: [
      {
        text: 'Workflow ID',
        align: 'start',
        value: 'workflow_id',
      },
      { text: 'Workflow Name', value: 'workflow_name' },
      { text: 'Dataset Name', value: 'dataset_name' },
      { text: 'Created', value: 'time_created' },
      { text: 'Updated', value: 'time_updated' },
      { text: 'Username', value: 'username' },
      { text: 'Owner Instance', value: 'kaapana_instance.instance_name' },
      { text: 'Status', value: 'status', align: 'center'},
      { text: 'Actions', value: 'actions', sortable: false, filterable: false, align: 'center'},
    ],
    expandedWorkflow: '',
    jobsofExpandedWorkflow: [],
    jobsofWorkflows: [],
    filteredJobState: undefined,
    manual_startID: '',
    abortID: '',
    restartID: '',
    deleteID: '',
    shouldExpand: true,
    shouldCollapse: true,
    localInstance: {},
    loading: false,
  }
},

mounted () {
  this.refreshClient();
  this.getLocalInstance();
},

props: {
  workflows: {
    type: Array,
    required: true
  },
  extLoading: {
    type: Boolean,
    required: true,
  }
},

computed: {
  filteredWorkflows() {  
    if (this.workflows !== null) {
      if (this.expandedWorkflow) {
        this.getJobsOfWorkflow(this.expandedWorkflow.workflow_name, this.filteredJobState)
      }
      return this.workflows
    }
  },
},

watch: {
  extLoading() {
    this.loading = this.extLoading
  }
},

methods: {
  // General Methods
  refreshClient() {
    this.$emit('refreshView')
  },
  checkForRemoteUpdates() {
    kaapanaApiService.syncRemoteInstances().then(successful => {
    })
  },
  expandRow(item) {
    if ( this.shouldExpand == true) {
      if (item === this.expanded[0]) {
        // Clicked row is already expanded, so collapse it
        if (this.shouldCollapse) {
          // but only if it is wanted to collapse row
          this.expanded = []
          this.filteredJobState = undefined
          this.expandedWorkflow = ''
          this.loading = false
        } else {
          this.shouldCollapse = true
          this.loading = false
        }
      } else {
        // Clicked row is not expanded, so expand it
        this.expanded = [item]
        this.expandedWorkflow = item
        if (!this.jobsofExpandedWorkflow) {
          this.getJobsOfWorkflow(this.expandedWorkflow.workflow_name, this.filteredJobState)
        }
      }
    } else {
      this.shouldExpand = true
      }
  },
  getStatesColorMap(item, darkTheme) {
    const states = item.workflow_jobs // .map(job => job.status)
    const colorMap = {
      'queued': 'grey',
      'scheduled': 'blue',
      'pending': 'orange',
      'running': 'green',
      'finished': darkTheme ? 'blue-grey': 'black' ,
      'failed': 'red'
    }
    return Object.entries(colorMap).map(([state, color]) => ({
      status: state,
      color: color,
      count: states.filter(_state => _state === state).length
    }))
  },
  redirectToAirflow() {
    const airflow_url = window.location.origin + "/flow/home"
    window.open(airflow_url, "_blank", "noreferrer")
  },
  startWorkflowManually(item) {
    this.shouldExpand = false
    this.manual_startID = item.workflow_id,
    console.log("Manually start Workflow: ", this.manual_startID)
    this.manuallyStartClientWorkflowAPI(this.manual_startID, 'confirmed')
  },
  abortWorkflow(item) {
      this.shouldExpand = false
      this.abortID = item.workflow_id
      console.log("Abort Workflow: ", this.abortID)
      this.abortClientWorkflowAPI(this.abortID, 'abort')
  },
  restartWorkflow(item) {
      this.shouldExpand = false
      this.restartID = item.workflow_id
      console.log("Restart Workflow: ", this.restartID)
      this.restartClientWorkflowAPI(this.restartID, 'scheduled')
  },
  deleteWorkflow(item) {
      this.shouldExpand = false
      this.deleteID = item.workflow_id
      console.log("Delete Workflow: ", this.deleteID, "Item:", item)
      this.deleteClientWorkflowAPI(this.deleteID)
  },

  // API Calls
  getLocalInstance() {
    kaapanaApiService
      .federatedClientApiGet("/kaapana-instance")
      .then((response) => {
        this.localInstance = response.data;
      })
      .catch((err) => {
        console.log(err);
      });
  },
  getJobsOfWorkflow(workflow_name, state, collapse=true) {
    if (typeof state !== "undefined") {
      this.filteredJobState = state;
    }
    this.loading = true
    if (!collapse) {
      this.shouldCollapse = collapse
    }
    kaapanaApiService
      .federatedClientApiGet("/jobs",{
        workflow_name: workflow_name,
        status: state,
      }).then((response) => {
        if (response.data.length !== 0) {
          this.loading = false
        } else {
          // no jobs could be get from backend from this workflow in this state
          // check whether workflow has at least any jobs
          this.getSingleJobOfWorkflow(workflow_name)
        }
        if (this.expanded.length > 0) {
          this.jobsofExpandedWorkflow = response.data;
        } else {
          this.jobsofWorkflows = response.data;
        }
      })
      .catch((err) => {
        this.loading = false
        console.log(err);
      })
  },
  getSingleJobOfWorkflow(workflow_name) {
    kaapanaApiService
      .federatedClientApiGet("/jobs",{
        workflow_name: workflow_name,
        limit: 1,
      }).then((response) => {
        if (response.data.length === 0) {
          const message_title = `No jobs for workflow ${workflow_name}`
          const message_text = `Workflow just triggered with >50 jobs? -> Jobs are created. \n
                                Workflow triggered >20 seconds ago?    -> Error while creating jobs.`
          this.$notify({
            type: "warning",
            title: message_title,
            text: message_text,
          })
        }
      })
      .catch((err) => {
        console.log(err);
      })
  },
  deleteClientWorkflowAPI(workflow_id) {
    this.loading = true
    kaapanaApiService
      .federatedClientApiDelete("/workflow",{
          workflow_id,
      }).then((response) => {
        this.loading = false
        // positive notification
        const message = `Successfully deleted workflow ${workflow_id}`
        this.$notify({
          type: 'success',
          title: message,
        })
      })
      .catch((err) => {
        this.loading = false
        // negative notification
        const message = `Error while deleting workflow ${workflow_id}`
        this.$notify({
          type: "error",
          title: message,
        })
        console.log(err);
      })
  },
  restartClientWorkflowAPI(workflow_id, workflow_status) {
    this.loading = true
    kaapanaApiService
      .federatedClientApiPut("/workflow",{
          workflow_id,
          workflow_status,
      }).then((response) => {
        this.loading = false
        // positive notification
        const message = `Successfully restarted workflow ${workflow_id}`
        this.$notify({
          type: "success",
          title: message,
        })
      })
      .catch((err) => {
        this.loading = false
        // negative notification
        const message = `Error while restarting workflow ${workflow_id}`
        this.$notify({
          type: "error",
          title: message,
        })
          console.log(err);
      })
  },
  abortClientWorkflowAPI(workflow_id, workflow_status) {
    this.loading = true
    kaapanaApiService
      .federatedClientApiPut("/workflow",{
          workflow_id,
          workflow_status,
      }).then((response) => {
        this.loading = false
        // positive notification
        const message = `Successfully aborted workflow ${workflow_id} and all its local jobs`
        this.$notify({
          type: "success",
          title: message,
        })
      })
      .catch((err) => {
        this.loading = false
        // negative notification
        const message = `Error while aborting workflow ${workflow_id}`
        this.$notify({
          type: "error",
          title: message,
        })
        console.log(err);
      })
  },
  manuallyStartClientWorkflowAPI(workflow_id, workflow_status) {
    this.loading = true
    kaapanaApiService
      .federatedClientApiPut("/workflow",{
          workflow_id,
          workflow_status,
      }).then((response) => {
        this.loading = false
        // positive notification
        const message = `Successfully manually started workflow ${workflow_id}` 
        this.$notify({
          type: "success",
          title: message,
        })
      })
      .catch((err) => {
        this.loading = false
        // negative notification
        const message = `Error while manually starting workflow ${workflow_id}`
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
