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
          <template v-slot:item.actions="{ item }">
            <v-menu>
              <template v-slot:activator="{ on, attrs }">
                <v-btn color="secondary" dark v-bind="attrs" v-on="on" >
                  Action
                </v-btn>
              </template>
              <v-list>
                <v-list-item @click='abortJob(item)' >
                  <v-list-item-title>Abort</v-list-item-title>
                </v-list-item>
                <v-list-item @click='restartJob(item)' >
                  <v-list-item-title>Restart</v-list-item-title>
                </v-list-item>
                <v-list-item @click='deleteJob(item)'>
                  <v-list-item-title>Delete</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
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
              text: 'Executing Instance Name',
              value: 'kaapana_instance.instance_name'
            })
            headers.push({
              text: 'Sender Instance Name',
              value: 'addressed_kaapana_instance_name'
            })
            headers.push({
              text: 'Conf',
              value: 'conf_data'
            })
            headers.push(
              { text: 'Status', value: 'status' },
              { text: 'Actions', value: 'actions', sortable: false },
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
      }
    }
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped lang="scss">

</style>
