<template>
    <v-container>
        <v-row>
            <h3>Jobs of expanded experiment</h3>
        </v-row>
        <v-dialog v-model="dialogConfData" width="600px"><template v-slot:activator="{ on, attrs }"></template>
          <v-card>
            <v-card-title class="text-h5 lighten-2">Conf object</v-card-title>
            <v-card-text class="text-left">
              <pre>{{ prettyConfData }}</pre>
            </v-card-text>
            <v-divider></v-divider>
            <v-card-actions>
              <v-spacer></v-spacer>
              <v-btn color="primary" text="" @click="dialogConfData = false">Close</v-btn>
            </v-card-actions>
          </v-card>
        </v-dialog>

        <v-data-table
          :headers="headers"
          :items="filteredJobs"
          :search="search"
          sort-by="time_updated"
          sort-desc="sort-desc"
          :hide-default-footer="true">
          <template v-slot:item.conf_data="{ item }">
            <v-icon color="secondary" dark="" @click="openConfData(item.conf_data)">
                mdi-email
            </v-icon>
          </template>
          <template v-slot:item.status="{ item }">
            <v-chip
              :color="getStatusColor(item.status)" dark="">{{ item.status }}
            </v-chip>
          </template>
          <template v-slot:item.airflow="{ item }">
            <v-tooltip bottom>
              <template v-slot:activator="{ on, attrs }">
                <v-btn v-bind="attrs" v-on="on" @click='direct_airflow_graph(item)' small icon>
                  <v-icon color="secondary" dark>mdi-chart-timeline-variant</v-icon>
                </v-btn>
              </template>
              <span>job's airflow dag_run graph view</span>
            </v-tooltip>
            <v-tooltip bottom>
              <template v-slot:activator="{ on, attrs }">
                <v-btn v-if="item.status == 'failed'" v-bind="attrs" v-on="on" @click='direct_airflow_operator_logs(item)' small icon>
                  <v-icon color="secondary" dark>mdi-alert-decagram-outline</v-icon>
                </v-btn>
              </template>
              <span>airflow logs of failed operator</span>
            </v-tooltip>
          </template>
          <template>hallo</template>
          <template v-slot:item.actions="{ item }">
            <v-col v-if="item.kaapana_instance.instance_name == item.owner_kaapana_instance_name" >
              <v-tooltip bottom>
                <template v-slot:activator="{ on, attrs }">
                  <v-btn v-bind="attrs" v-on="on" @click='abortJob(item)' small icon>
                    <v-icon color="secondary" dark>mdi-stop-circle-outline</v-icon>
                  </v-btn>
                </template>
                <span>abort single job</span>
              </v-tooltip>
              <v-tooltip bottom>
                <template v-slot:activator="{ on, attrs }">
                  <v-btn v-bind="attrs" v-on="on" @click='restartJob(item)' small icon>
                    <v-icon color="secondary" dark>mdi-rotate-left</v-icon>
                  </v-btn>
                </template>
                <span>restart single job</span>
              </v-tooltip>
              <v-tooltip bottom>
                <template v-slot:activator="{ on, attrs }">
                  <v-btn v-bind="attrs" v-on="on" @click='deleteJob(item)' small icon>
                    <v-icon color="secondary" dark>mdi-trash-can-outline</v-icon>
                  </v-btn>
                </template>
                <span>delete single job</span>
              </v-tooltip>
            </v-col>
            <div v-else>
              <v-tooltip bottom>
                <template v-slot:activator="{ on, attrs }">
                  <v-icon color="secondary" dark v-bind="attrs" v-on="on">
                    mdi-cloud-braces
                  </v-icon>
                </template>
                <span>No actions for REMOTE job!</span>
              </v-tooltip>
            </div>
          </template>
        </v-data-table>

    </v-container>
</template>
  
<script>
    import kaapanaApiService from "@/common/kaapanaApi.service";

    export default {
      name: "JobTable",

      data: () => ({
        dialogConfData: false,
        dialogDelete: false,
        prettyConfData: {},
        jobStatus: 'all',
        search: "",
        abortID: '',
        restartID: '',
        deleteID: '',
        airflow_url: '',
        dag_run_datetime: '',
        dag_run_ms: '',
        dag_run_tasks_n_states: {},
      }),

      props: {
        jobs: {
          type: Array,
          required: true
        },
        remote: {
          type: Boolean,
          default: true
        },
      },

      computed: {
        filteredJobs() {
          if (this.jobs !== null) {
            console.log("filteredJobs", this.jobs)
            return this.jobs.filter((i) => {
              let statusFilter = false;
              if (i.status == this.jobStatus) {
                statusFilter = true
              }
              if (this.jobStatus == 'all') {
                statusFilter = true
              }
              return statusFilter
            });
          } else {
            console.log("No jobs")
            return [];
          }
        },
        headers() {
            let headers = []
            headers.push({
              text: 'Dag ID',
              value: 'dag_id'
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
              text: 'Runner Instance',
              value: 'kaapana_instance.instance_name'
            })
            headers.push({
              text: 'Owner Instance',
              value: 'owner_kaapana_instance_name'
            })
            headers.push({
              text: 'Conf',
              value: 'conf_data',
            })
            headers.push(
              { text: 'Status', value: 'status', align: 'center'},
              { text: 'Logs', value: 'airflow', sortable: false , align: 'center'},
              { text: 'Actions', value: 'actions', sortable: false , align: 'center'},
            ) 
            return headers
          }
      },

      watch: {
        dialogConfData (val) {
          val || this.closeConfData()
        },    
      },

      methods: {
        // General Methods
        openConfData (conf_data) {
          this.prettyConfData = conf_data
          this.dialogConfData = true
        },
        closeConfData () {
          this.dialogConfData = false
        },
        getStatusColor(status) {
          console.log("Status:", status)
          if (status == 'queued') {
            return 'grey'
          } else if (status == 'pending') {
            return 'orange'
          } else if (status == 'scheduled') {
            return 'blue'
          } else if (status == 'running') {
            return 'green'
          } else if (status == 'finished') {
            return 'black'
          } else {
            return 'red'
          }
        },
        abortJob(item) {
            this.abortID = item.id
            console.log("Abort Job:", this.abortID, "Item:", item)
            this.abortJobAPI(this.abortID, 'abort', 'The worklow was aborted!')
        },
        restartJob(item) {
            this.restartID = item.id
            console.log("Restart Job:", this.restartID, "Item:", item)
            this.restartJobAPI(this.restartID, 'scheduled', 'The worklow was triggered!')
        },
        deleteJob(item) {
            this.deleteID = item.id
            console.log("Delete Job:", this.deleteID, "Item:", item)
            this.deleteJobAPI(this.deleteID)
        },
        direct_airflow_graph(item) {
          this.dag_run_datetime = item.run_id.split("-").at(-1)
          this.dag_run_datetime = this.dag_run_datetime.slice(-6).slice(0, 2) + "." + this.dag_run_datetime.slice(-4)
          this.dag_run_ms = item.run_id.split("-").at(-1).slice(-6).slice(0, 2) + this.dag_run_datetime.slice(-4)
          this.dag_run_datetime = item.time_updated.slice(0, 19) + "." + this.dag_run_ms + "+00:00"
          this.airflow_url = item.kaapana_instance.protocol + "://" + item.kaapana_instance.host + "/flow/graph?dag_id=" + item.dag_id + "&execution_date=" + encodeURIComponent(this.dag_run_datetime)
          window.open(this.airflow_url, "_blank", "noreferrer")
        },
        async direct_airflow_operator_logs(item) {     // async to make await work properly
          await this.getJobTaskinstancesAPI(item.id);  // task_instances and states are written to -> this.dag_run_tasks_n_states ; needs to be await to asve API result to variable

          console.log("this.dag_run_tasks_n_states: ", this.dag_run_tasks_n_states)
          console.log("typeof: ", typeof this.dag_run_tasks_n_states)
          // iterate over this.dag_run_tasks_n_states and search for operator with state 'failed'
          for (let key in this.dag_run_tasks_n_states) {
            console.log(key, this.dag_run_tasks_n_states[key])
            if (this.dag_run_tasks_n_states[key].at(-1) == "failed") {
              this.failed_operator = key // .split(".")[-1]
              console.log("failed_operator: ", this.failed_operator)
            }
          }
          // compose airflow log link:
          this.dag_run_datetime = this.dag_run_tasks_n_states[this.failed_operator].at(0)
          this.airflow_url = item.kaapana_instance.protocol + "://" + item.kaapana_instance.host + "/flow/log?dag_id=" + item.dag_id + "&task_id=" + this.failed_operator + "&execution_date=" + encodeURIComponent(this.dag_run_datetime)
          window.open(this.airflow_url, "_blank", "noreferrer")
        },
        
        // API Calls
        abortJobAPI(job_id, status, description) {
          kaapanaApiService
            .federatedClientApiPut("/job", {
              job_id,
              status,
              description,
            })
            .then((response) => {
              this.$emit('refreshView')
            })
            .catch((err) => {
              console.log(err);
            });
        },
        restartJobAPI(job_id, status, description) {
          kaapanaApiService
            .federatedClientApiPut("/job", {
              job_id,
              status,
              description,
            })
            .then((response) => {
              this.$emit('refreshView')
            })
            .catch((err) => {
              console.log(err);
            });
        },
        deleteJobAPI(job_id) {
          kaapanaApiService
            .federatedClientApiDelete("/job", {
              job_id,
            })
            .then((response) => {
              this.$emit('refreshView')
              console.log("Job deleted")
            })
            .catch((err) => {
              console.log(err);
            });
        },
        async getJobTaskinstancesAPI(job_id) {
          console.log("Trying to catch task_instances of job: ", job_id),
          await kaapanaApiService
            .federatedClientApiGet("/get_job_taskinstances", {
              job_id,
            })
            .then((response) => {
              this.dag_run_tasks_n_states = response.data
              console.log("response in getJobTaskinstancesAPI: ", this.dag_run_tasks_n_states)
              // this.$emit('refreshView')
            })
            .catch((err) => {
              console.log(err);
            });
        },
        

      }
    }
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped lang="scss">

</style>
