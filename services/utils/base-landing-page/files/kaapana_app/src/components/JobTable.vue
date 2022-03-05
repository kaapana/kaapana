
<template lang="pug">
    v-card
      v-card-title
        v-row
          v-col(cols="6")
            span Jobs
          v-col(cols="2")
            v-select(
              label="Status",
              :items="['all', 'queued', 'pending', 'scheduled', 'running', 'finished', 'failed']",
              v-model="jobStatus",
              hide-details=""
            )
          v-col(cols="4")
            v-text-field(
              v-model="search",
              append-icon="mdi-magnify",
              label="Search",
              hide-details=""
            )
      v-data-table(:headers='headers' :items='filteredJobs' :search="search" sort-by='time_updated' sort-desc=true)
        template(v-slot:item.status='{ item }')
          v-chip(:color='getStatusColor(item.status)' dark='') {{ item.status }}
        template(v-slot:item.actions='{ item }')
          v-btn(v-if='remote==false && item.status=="pending"', @click='executeJob(item)') Set to scheduled
          v-btn(v-if='remote==false', @click='deleteJob(item)') Delete job
          v-btn(v-if='remote==true && (item.status=="queued")', @click='deleteJob(item)') Delete job
          //- v-btn(v-if='remote==false && (item.status=="pending" || item.status=="finished" || item.status=="failed")', @click='deleteJob(item)') Delete job
          //- v-btn(v-if='remote==true && (item.status=="queued")', @click='deleteJob(item)') Delete job
</template>

<script>

import kaapanaApiService from "@/common/kaapanaApi.service";

export default {
  name: 'JobTable',
  data: () => ({
    dialogDelete: false,
    // headers: [
    //   { text: 'Description', align: 'start', value: 'description' },
    //   { text: 'Status', value: 'status' },
    //   { text: 'Actions', value: 'actions', sortable: false },
    // ],
    search: "",
    jobStatus: 'all'
  }),
  props: {
    jobs: {
      type: Array,
      required: true
    },
    remote: {
      type: Boolean,
      default: true
    }
  },
  computed: {
    filteredJobs() {
      if (this.jobs !== null) {
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
        return [];
      }
    },
    headers() {
      let headers = []
      headers.push({
        text: 'Dag id',
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
        text: 'Executing Node id',
        value: 'kaapana_instance.node_id'
      })
      headers.push({
        text: 'Sender Node Id',
        value: 'addressed_kaapana_node_id'
      })
      headers.push(
        { text: 'Description', align: 'start', value: 'description' },
        { text: 'Status', value: 'status' },
        { text: 'Actions', value: 'actions', sortable: false },
      ) 
      return headers
    }
  },
  methods: {
    executeJob(item) {
      kaapanaApiService
        .federatedClientApiPut("/job", {
          job_id: item.id,
          status: 'scheduled',
          description:'The worklow was triggered!',
          // addressed_kaapana_node_id: item.addressed_kaapana_node_id,
          // external_job_id: item.external_job_id
        })
        .then((response) => {
          this.$emit('refreshView')
        })
        .catch((err) => {
          console.log(err);
        });
    },
    deleteJob(item) {
      kaapanaApiService
        .federatedClientApiDelete("/job", {
          job_id: item.id,
        })
        .then((response) => {
          this.$emit('refreshView')
          // if (this.remote == false) {
          //   // ToDo needst to reach the outside world!
          //   kaapanaApiService
          //     .federatedRemoteApiDelete("/job", {
          //       job_id: item.external_job_id,
          //     })
          //     .then((response) => {
          //       this.$emit('refreshView')
          //     })
          //     .catch((err) => {
          //       console.log(err);
          //     });
          // }
        })
        .catch((err) => {
          console.log(err);
        });

    },
    getStatusColor(status) {
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
  }
}
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped lang="scss">

</style>
