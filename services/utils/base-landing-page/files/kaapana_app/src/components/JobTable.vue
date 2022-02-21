
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
      v-data-table(:headers='headers' :items='filteredJobs' :search="search" sort-by='status')
        template(v-slot:item.status='{ item }')
          v-chip(:color='getStatusColor(item.status)' dark='') {{ item.status }}
        template(v-slot:item.actions='{ item }')
          v-btn(v-if='remote==false && item.status=="pending"', @click='setToScheduled(item)') Set to scheduled
          v-btn(v-if='remote==false && item.status=="scheduled"', @click='executeJob(item)') Execute job
          v-btn(v-if='remote==false && (item.status=="pending" || item.status=="scheduled" || item.status=="finished" || item.status=="failed")', @click='deleteJob(item)') Delete job
          v-btn(v-if='remote==true && (item.status=="queued" || item.status=="finished" || item.status=="failed")', @click='deleteJob(item)') Delete job
</template>

<script lang="ts">

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
    filteredJobs(): any {
      if (this.jobs !== null) {
        return this.jobs.filter((i: any) => {
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
    headers(): any {
      let headers = []
      if (this.remote==false) {
        headers.push({
          text: 'Remote Node Id',
          value: 'addressed_kaapana_node_id'
        })
      } else {
        headers.push({
          text: 'Node id',
          value: 'kaapana_instance.node_id'
        })
      }
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
        .federatedClientApiPost("/execute-scheduled-job", null, {
          job_id: item.id,
        })
        .then((response: any) => {
          this.$emit('refreshView')
    	    // this.$emit('gci')
        })
        .catch((err: any) => {
          console.log(err);
        });
    },
    deleteJob(item) {
      kaapanaApiService
        .federatedClientApiDelete("/job", {
          job_id: item.id,
        })
        .then((response: any) => {
        })
        .catch((err: any) => {
          console.log(err);
        });
      if (this.remote == false) {
        kaapanaApiService
          .federatedRemoteApiDelete("/job", {
            job_id: item.external_job_id,
          })
          .then((response: any) => {
          })
          .catch((err: any) => {
            console.log(err);
          });
      }
      this.$emit('refreshView')
    },
    setToScheduled(item) {
      kaapanaApiService
        .federatedRemoteApiPut("/job", {
          job_id: item.external_job_id,
          status: 'scheduled'
        })
        .then((response: any) => {
          this.$emit('refreshView')
    	    // this.$emit('gci')
        })
        .catch((err: any) => {
          console.log(err);
        });

      kaapanaApiService
        .federatedClientApiPut("/job", {
          job_id: item.id,
          status: 'scheduled'
        })
        .then((response: any) => {
          this.$emit('refreshView')
    	    // this.$emit('gci')
        })
        .catch((err: any) => {
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
