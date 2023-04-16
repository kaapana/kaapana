
<template lang="pug">
  v-card(max-width="800px")
    v-card-title 
      v-col(align="left")
        p Instance name: {{ instance.instance_name }}
      v-col(align="right")
        v-tooltip(v-if="remote" bottom='')
          template(v-slot:activator='{ on, attrs }')
            v-icon(:color="diff_updated" small dark='' v-bind='attrs' v-on='on')
               | mdi-circle
          span Time since last update: green: 5 min, yellow: 1 hour, orange: 5 hours, else red)
    v-card-text(class=text-primary)
      //- Network or rather port: edit mode
      v-row(v-if="edit_port" align="center")
        v-col(cols=4 align="left") Network:
        v-col( align="left")
          v-text-field(v-model="instancePost.port" label="Port" required="")
        v-col(cols=1 align="center")
          v-btn(@click="edit_port = !edit_port; updateRemoteInstanceForm();" small icon)
            v-icon mdi-content-save
      //- display mode
      v-row(v-else)
        v-col(cols=4 align="left") Network: 
        v-col( align="left") {{ instancePost.protocol }}://{{ instancePost.host }}:{{ instancePost.port }}
        v-col(cols=1 align="center")
          v-btn(@click="edit_port = !edit_port" small icon)
            v-icon mdi-pencil   
      //- Token: edit mode
      v-row(v-if="edit_token" align="center")
        v-col(cols=4 align="left") Token:
        v-col( align="left")
          v-text-field(v-model="instancePost.token" label="Token" required="")
        v-col(cols=1 align="center")
          v-btn(@click="edit_token = !edit_token; updateRemoteInstanceForm();" small icon)
            v-icon mdi-content-save
      //- display mode 
      v-row(v-else)
        v-col(cols=4 align="left") Token: 
        v-col( align="left") {{ instancePost.token }}
        v-col(cols=1 align="center")
          v-btn(@click="edit_token = !edit_token" small icon)
            v-icon mdi-pencil
      v-row 
        v-col(cols=4 align="left") Created: 
        v-col( align="left") {{ instance.time_created }}
        //- v-col(cols=1)
      v-row 
        v-col(cols=4 align="left") Updated: 
        v-col( align="left") {{ instance.time_updated }}
        //- v-col(cols=1)
      //- SSL: edit mode
      v-row(v-if="edit_ssl_check" align="center")
        v-col(cols=4 align="left") SSL:
        v-col( align="left")
          v-checkbox(v-model="instancePost.ssl_check" label="SSL"  required='')
        v-col(cols=1 align="center")
          v-btn(@click="edit_ssl_check = !edit_ssl_check; updateRemoteInstanceForm();" small icon)
            v-icon mdi-content-save
      //- display mode
      v-row(v-else)
        v-col(cols=4 align="left") SSL:
        v-col( align="left")
          v-icon(v-if="instancePost.ssl_check" small color="green") mdi-check-circle
          v-icon(v-if="!instancePost.ssl_check" small) mdi-close-circle
        v-col(cols=1 align="center")
          v-btn(@click="edit_ssl_check = !edit_ssl_check" small icon)
            v-icon mdi-pencil        
      //- Fernet key: edit mode
      v-row(v-if="edit_fernet_encrypted" align="center")
        v-col(cols=4 align="left") Fernet key:
        v-col( align="left")
          v-checkbox(v-model="instancePost.fernet_encrypted" label="Fernet encrypted"  required='')
        v-col(cols=1 align="center")
          v-btn(@click="edit_fernet_encrypted = !edit_fernet_encrypted; updateRemoteInstanceForm();" small icon)
            v-icon mdi-content-save
      //- display mode
      v-row(v-else)
        v-col(cols=4 align="left") Fernet key:
        v-col( align="left")
          div {{ instancePost.fernet_key }}
        v-col(cols=1 align="center")
          v-btn(@click="edit_fernet_encrypted = !edit_fernet_encrypted" small icon)
            v-icon mdi-pencil
      //- Sync remote jobs: display mode
      v-row
        v-col(cols=4 align="left") Sync remote jobs:
        v-col( align="left")
          v-icon(v-if="instancePost.automatic_update" small color="green") mdi-check-circle
          v-icon(v-if="!instancePost.automatic_update" small) mdi-close-circle
        //- v-col(cols=1 align="center")
      //- Autmoatically execute pending jobs: display mode
      v-row
        v-col(cols=4 align="left") Autmoatically execute pending jobs:
        v-col( align="left")
          v-icon(v-if="instancePost.automatic_exp_execution" small color="green") mdi-check-circle
          v-icon(v-if="!instancePost.automatic_exp_execution" small) mdi-close-circle
        //- v-col(cols=1 align="center")
      //- Allowed DAGs: display mode
      v-row
        v-col(cols=4 align="left") Allowed DAGs:
        v-col( align="left")
          v-chip(v-for='dag in instancePost.allowed_dags' small) {{dag}}
        //- v-col(cols=1 align="center")
      //- Allowed Datasets: display mode
      v-row
        v-col(cols=4 align="left") Allowed Datasets:
        v-col( align="left")
          v-chip(v-for='dataset in instancePost.allowed_datasets' small) {{dataset}}
        //- v-col(cols=1 align="center")
    v-card-actions
      v-tooltip(bottom)
        template(v-slot:activator="{ on, attrs }")
          v-btn(v-bind="attrs" v-on="on" @click='deleteInstance()' small icon)
           v-icon(color="red" dark) mdi-trash-can-outline
        span delete instance
    v-dialog(v-model='dialogDelete' max-width='500px')
      v-card
        v-card-title.text-h5 Are you sure you want to delete this instance. With it all corresponding jobs are deleted?
        v-card-actions
          v-spacer
          v-btn(color='primary' text='' @click='closeDelete') Cancel
          v-btn(color='primary' text='' @click='deleteInstanceConfirm') OK
          v-spacer
  
</template>
  
  <script>
  
  import kaapanaApiService from "@/common/kaapanaApi.service";
  import {loadDatasetNames} from "@/common/api.service";
  
  
  export default {
    name: 'RemoteKaapanaInstance',
    data: () => ({
      dialogOpen: false,
      dialogDelete: false,
      // clientDialog: false,
      dags: [],
      datasets: [],
      instancePost: {
        ssl_check: false,
        automatic_update: false,
        automatic_exp_execution: false,
        fernet_encrypted: false,
        allowed_dags: [],
        allowed_datasets: []
      },
      edit_ssl_check: false,
      edit_fernet_encrypted: false,
      edit_port: false,
      edit_token: false,
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
      time_updated: { // needed to always re-render the remote instance whenever parent component gets remote instance from backend
        type: String,
        required: true
      },
    },
    mounted () {
      this.lets_init()
    },
    watch: {
      dialogDelete (val) {
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
        var datetime = Date.parse(new Date(this.instance.time_updated).toUTCString()); // var datetime = Date.parse(new Date(this.instance.time_updated * 1000).toUTCString());
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
      lets_init () {
        this.instance_names = []
        this.experiment_name = null
        this.dag_id = null
        this.external_instance_names = []
        this.instancePost = this.instance
        this.instancePost.fernet_encrypted = false
        console.log('Getting Dags and Datasets')
        this.getDags();
        this.getDatasets();
      },
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
        loadDatasetNames().then(_datasetNames => {
          this.datasets = _datasetNames;
        })
      },
      updateRemoteInstanceForm() {
        kaapanaApiService
          .federatedClientApiPut("/remote-kaapana-instance", this.instancePost)
          .then((response) => {
            console.log("ClientForm updated")
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
  