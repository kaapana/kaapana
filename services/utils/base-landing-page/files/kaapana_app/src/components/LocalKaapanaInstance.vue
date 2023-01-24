
<template lang="pug">
v-dialog(v-model='dialogOpen' max-width='600px')
  //-  :persistent=dialogPersistence ;  :persistent='isPersistent' ; @close="dialogClose()" 
  template(v-if="!remote" v-slot:activator='{on, attrs}')
    v-btn(x-large color="primary" v-bind='attrs' v-on='on' dark) 
      strong
        h3 Local Instance: {{ instance.instance_name }}
  v-card
    v-card-title Instance name: {{ instance.instance_name }}
      //- v-spacer
      v-tooltip(v-if="remote" bottom='')
        template(v-slot:activator='{ on, attrs }')
          v-icon(:color="diff_updated" small dark='' v-bind='attrs' v-on='on')
            | mdi-circle
        span Time since last update: green: 5 min, yellow: 1 hour, orange: 5 hours, else red)
    v-card-text(class=text-primary)
      v-row(align="start")
        v-col(align="left") Network: 
        v-col(cols=6 align="left") {{ instance.protocol }}://{{ instance.host }}:{{ instance.port }}
        v-col(cols=1)
      v-row 
        v-col(align="left") Token: 
        v-col(cols=6 align="left") {{ instance.token }}
        v-col(cols=1)
      v-row 
        v-col(align="left") Created: 
        v-col(cols=6 align="left") {{ instance.time_created }}
        v-col(cols=1)
      v-row 
        v-col(align="left") Updated: 
        v-col(cols=6 align="left") {{ instance.time_updated }}
        v-col(cols=1)
      //- SSL: edit mode
      v-row(v-if="edit_ssl_check" align="center")
        v-col(align="left") SSL:
        v-col(cols=6 align="left")
          v-checkbox(v-model="clientPost.ssl_check" label="SSL"  required='')
        v-col(cols="1" align="center")
          v-btn(@click="edit_ssl_check = !edit_ssl_check; updateClientForm();" small icon)
            v-icon mdi-content-save
      //- display mode
      v-row(v-else)
        v-col(align="left") SSL:
        v-col(cols=6 align="left")
          v-icon(v-if="clientPost.ssl_check" small color="green") mdi-check-circle
          v-icon(v-if="!clientPost.ssl_check" small) mdi-close-circle
        v-col(cols="1" align="center")
          v-btn(@click="edit_ssl_check = !edit_ssl_check" small icon)
            v-icon mdi-pencil        
      //- Fernet key: edit mode
      v-row(v-if="edit_fernet_encrypted" align="center")
        v-col(align="left") Fernet key:
        v-col(cols=6 align="left")
          v-checkbox(v-model="clientPost.fernet_encrypted" label="Fernet encrypted"  required='')
        v-col(cols="1" align="center")
          v-btn(@click="edit_fernet_encrypted = !edit_fernet_encrypted; updateClientForm();" small icon)
            v-icon mdi-content-save
      //- display mode
      v-row(v-else)
        v-col(align="left") Fernet key:
        v-col(cols=6 align="left")
          div {{ clientPost.fernet_key }}
        v-col(cols="1" align="center")
          v-btn(@click="edit_fernet_encrypted = !edit_fernet_encrypted" small icon)
            v-icon mdi-pencil
      //- Sync remote jobs: edit mode
      v-row(v-if="edit_automatic_update" align="center")
        v-col(align="left") Sync remote jobs:
        v-col(cols=6 align="left")
          v-checkbox(v-model="clientPost.automatic_update" label="Check automatically for remote updates")
        v-col(cols="1" align="center")
          v-btn(@click="edit_automatic_update = !edit_automatic_update; updateClientForm();" small icon)
            v-icon mdi-content-save
      //- display mode
      v-row(v-else)
        v-col(align="left") Sync remote jobs:
        v-col(cols=6 align="left")
          v-icon(v-if="clientPost.automatic_update" small color="green") mdi-check-circle
          v-icon(v-if="!clientPost.automatic_update" small) mdi-close-circle
        v-col(cols="1" align="center")
          v-btn(@click="edit_automatic_update = !edit_automatic_update" small icon)
            v-icon mdi-pencil
      //- Autmoatically execute pending jobs: edit mode
      v-row(v-if="edit_automatic_job_execution" align="center")
        v-col(align="left") Autmoatically execute pending jobs:
        v-col(cols=6 align="left")
          v-checkbox(v-model="clientPost.automatic_job_execution" label="Execute automatically jobs")
        v-col(cols="1" align="center")
          v-btn(@click="edit_automatic_job_execution = !edit_automatic_job_execution; updateClientForm();" small icon)
            v-icon mdi-content-save
      //- display mode
      v-row(v-else)
        v-col(align="left") Autmoatically execute pending jobs:
        v-col(cols=6 align="left")
          v-icon(v-if="clientPost.automatic_job_execution" small color="green") mdi-check-circle
          v-icon(v-if="!clientPost.automatic_job_execution" small) mdi-close-circle
        v-col(cols="1" align="center")
          v-btn(@click="edit_automatic_job_execution = !edit_automatic_job_execution" small icon)
            v-icon mdi-pencil
      //- Allowed DAGs: edit mode
      v-row(v-if="edit_allowed_dags" align="center")
        v-col(align="left") Allowed DAGs:
        v-col(cols=6 align="left")
          v-select(v-model='clientPost.allowed_dags' :items='dags' label='Allowed dags' multiple='' chips='' hint='Which dags are allowed to be triggered' persistent-hint='')
          //- span( v-for='dag in instance.allowed_dags') {{dag}}
        v-col(cols="1" align="center")
          v-btn(@click="edit_allowed_dags = !edit_allowed_dags; updateClientForm();" small icon)
            v-icon mdi-content-save
      //- display mode
      v-row(v-else)
        v-col(align="left") Allowed DAGs:
        v-col(cols=6 align="left")
          v-chip(v-for='dag in clientPost.allowed_dags' small) {{dag}}
        v-col(cols="1" align="center")
          v-btn(@click="edit_allowed_dags = !edit_allowed_dags" small icon)
            v-icon mdi-pencil
      //- Allowed Datasets: edit mode
      v-row(v-if="edit_allowed_datasets" align="center")
        v-col(align="left") Allowed Datasets:
        v-col(cols=6 align="left")
          v-select(v-model='clientPost.allowed_datasets' :items='datasets' label='Allowed datasets' multiple='' chips='' hint='Which datasets are allowed to be used' persistent-hint='')
        v-col(cols="1" align="center")
          v-btn(@click="edit_allowed_datasets = !edit_allowed_datasets; updateClientForm();" small icon)
            v-icon mdi-content-save
      //- display mode
      v-row(v-else)
        v-col(align="left") Allowed Datasets:
        v-col(cols=6 align="left")
          v-chip(v-for='dataset in clientPost.allowed_datasets' small) {{dataset}}
        v-col(cols="1" align="center")
          v-btn(@click="edit_allowed_datasets = !edit_allowed_datasets" small icon)
            v-icon mdi-pencil
    v-card-actions
      //- v-btn(color='primary' @click="editInstance()" dark) Edit Instance
      v-btn(color='red' @click="deleteInstance()" dark) Delete instance    
  
    v-dialog(v-model='dialogDelete' max-width='500px')
      v-card
        v-card-title.text-h5 Are you sure you want to delete this instance. With it all corresponding jobs and experiments are deleted?
        v-card-actions
          v-spacer
          v-btn(color='blue darken-1' text='' @click='closeDelete') Cancel
          v-btn(color='blue darken-1' text='' @click='deleteInstanceConfirm') OK
          v-spacer
  
</template>
  
  <script>
  
  import kaapanaApiService from "@/common/kaapanaApi.service";
  
  
  export default {
    name: 'LocalKaapanaInstance',
    data: () => ({
      dialogOpen: false,
      dialogDelete: false,
      // clientDialog: false,
      dags: [],
      datasets: [],
      clientPost: {
        ssl_check: false,
        automatic_update: false,
        automatic_job_execution: false,
        fernet_encrypted: false,
        allowed_dags: [],
        allowed_datasets: []
      },
      edit_ssl_check: false,
      edit_automatic_update: false,
      edit_automatic_job_execution: false,
      edit_fernet_encrypted: false,
      edit_allowed_dags: false,
      edit_allowed_datasets: false,
    }),
    props: {
      instance: {
        type: Object,
        required: true
      },
      remote: { // false for client instance; true for remote instances
        type: Boolean,
        required: true
      },
    },
    watch: {
      dialogOpen () {
        this.instance_names = []
        this.experiment_name = null
        this.dag_id = null
        this.external_instance_names = []
        this.clientPost = this.instance
        this.clientPost.fernet_encrypted = false
        console.log("clientPost: ", this.clientPost)
        console.log('Getting Dags and Datasets')
        this.getDags();
        this.getDatasets();
      },
      dialogDelete (val) {
        console.log("dialogDelete")
        val || this.closeDelete()
      },
    },
    computed: {
      instance_time_created() {
        return new Date(this.instance.time_created * 1000).toUTCString();
      },
      instance_time_updated() {
        return new Date(this.instance.time_updated * 1000).toUTCString();
      },
      utc_timestamp() {
        return Date.parse(new Date().toUTCString());
      },
      diff_updated() {
        var datetime = Date.parse(new Date(this.instance.time_updated * 1000).toUTCString());
        var now = Date.parse(new Date().toUTCString());
  
        if( isNaN(datetime) )
        {
            return "";
        }
        var diff_in_seconds = (now - datetime) / 1000
  
        if (diff_in_seconds < (60*5)) {
          return 'green'
        } else if (diff_in_seconds < (60*60)) {
          return 'yellow'
        } else if (diff_in_seconds < (60*60*5)) {
          return 'orange'
        } else {
          return 'red'
        }
      }
    },
    methods:{
      closeDelete() {
        this.dialogDelete = false
      },
      editInstance() {
        this.$emit('ei', this.instance)
      },
      deleteInstanceConfirm () {
        let params = {
          kaapana_instance_id: this.instance.id,
        };
        kaapanaApiService
          .federatedClientApiDelete("/kaapana-instance", params)
          .then((response) => {
            this.$emit('refreshView')
            this.closeDelete()
          })
          .catch((err) => {
            console.log(err);
          });
      },
      deleteInstance() {
        this.dialogDelete = true
      },
      getDags() {
        kaapanaApiService
          .federatedClientApiPost("/get-dags", {remote: false})
          .then((response) => {
            this.dags = response.data;
          })
          .catch((err) => {
            console.log(err);
          });
      },
      getDatasets() {
        kaapanaApiService
          .federatedClientApiGet("/cohort-names")
          .then((response) => {
            this.datasets = response.data;
          })
          .catch((err) => {
            console.log(err);
          });
      },
      updateClientForm() {
        console.log("clientPost: ", this.clientPost)
        kaapanaApiService
          .federatedClientApiPut("/client-kaapana-instance", this.clientPost)
          .then((response) => {
            console.log("ClientForm updated")
            // this.clientUpdate = false
            // this.clientDialog = false
            // get_remote_updates
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
  