
<template lang="pug">
  v-card
    v-card-title
     v-row(align="center")
      v-col(cols=9)
        p Instance name: {{ instance.instance_name }}
      v-col(align="right")
        p
          v-tooltip(bottom v-if="remote")
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
      v-col(align="right")
        p
          v-tooltip(v-if="!remote" bottom='')
            template(v-slot:activator='{ on, attrs }')
              v-icon(color="primary" dark='' v-bind='attrs' v-on='on')
                | mdi-home
            span your local instance: {{ instance.instance_name }}
          v-tooltip(v-if="remote" bottom='')
            template(v-slot:activator='{ on, attrs }')
              v-icon(color="primary" dark='' v-bind='attrs' v-on='on')
                | mdi-cloud-braces
            span remote instance: {{ instance.instance_name }}
      v-col(align="right")
        p
          v-tooltip(v-if="remote" bottom='')
            template(v-slot:activator='{ on, attrs }')
              v-icon(:color="diff_updated" small dark='' v-bind='attrs' v-on='on')
                | mdi-circle
            span Time since last update: green: 5 min, yellow: 1 hour, orange: 5 hours, else red
    v-card-text(class=text-primary)
      //- Network or rather port: edit mode
      v-row(v-if="edit_port" align="center")
        v-col(cols=4 align="left") Network:
        v-col( align="left")
          v-text-field(v-model="instancePost.port" label="Port" required="")
        v-col(cols=1 align="center")
          v-btn(@click="edit_port = !edit_port; updateInstanceForm();" small icon)
            v-icon mdi-content-save
      //- display mode
      v-row(v-else)
        v-col(cols=4 align="left") Network: 
        v-col( align="left") {{ instancePost.protocol }}://{{ instancePost.host }}:{{ instancePost.port }}
        v-col(v-if="remote" cols=1 align="center")
          v-btn(@click="edit_port = !edit_port" small icon)
            v-icon mdi-pencil   
      //- Token: edit mode
      v-row(v-if="edit_token" align="center")
        v-col(cols=4 align="left") Token:
        v-col( align="left")
          v-text-field(v-model="instancePost.token" label="Token" required="")
        v-col(cols=1 align="center")
          v-btn(@click="edit_token = !edit_token; updateInstanceForm();" small icon)
            v-icon mdi-content-save
      //- display mode 
      v-row(v-else)
        v-col(cols=4 align="left") Token: 
        v-col( align="left") {{ instancePost.token }}
        v-col(v-if="remote" cols=1 align="center")
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
        v-col(cols=4 align="left") Verify SSL:
        v-col( align="left")
          v-checkbox(v-model="instancePost.ssl_check" label="Verify SSL"  required='')
        v-col(cols=1 align="center")
          v-btn(@click="edit_ssl_check = !edit_ssl_check; updateInstanceForm();" small icon)
            v-icon mdi-content-save
      //- display mode
      v-row(v-else)
        v-col(cols=4 align="left") Verify SSL:
        v-col( align="left")
          v-icon(v-if="instancePost.ssl_check" small color="green") mdi-check-circle
          v-icon(v-if="!instancePost.ssl_check" small) mdi-close-circle
        v-col(cols=1 align="center")
          v-btn(@click="edit_ssl_check = !edit_ssl_check" small icon)
            v-icon mdi-pencil        
      //- Fernet key: edit mode
      v-row(v-if="edit_fernet_encrypted" align="center")
        v-col(cols=4 align="left") Fernet key:
        v-col(align="left")
          v-checkbox(v-if="!remote" v-model="instancePost.fernet_encrypted" label="Fernet encrypted"  required='')
          v-text-field(v-if="remote" v-model="instancePost.fernet_key" label="Fernet key")
        v-col(cols=1 align="center")
          v-btn(@click="edit_fernet_encrypted = !edit_fernet_encrypted; updateInstanceForm();" small icon)
            v-icon mdi-content-save
      //- display mode
      v-row(v-else)
        v-col(cols=4 align="left") Fernet key:
        v-col( align="left")
          div {{ instancePost.fernet_key }}
        v-col(cols=1 align="center")
          v-btn(@click="edit_fernet_encrypted = !edit_fernet_encrypted" small icon)
            v-icon mdi-pencil
          //- Sync remote: edit mode
      v-row(v-if="edit_automatic_update" align="center")
        v-col(cols=4  align="left") Automatically sync remotes:
        v-col(align="left")
          v-checkbox(v-model="instancePost.automatic_update" label="Check automatically for remote updates")
        v-col(cols=1 align="center")
          v-btn(@click="edit_automatic_update = !edit_automatic_update; updateInstanceForm();" small icon)
            v-icon mdi-content-save
      //- display mode
      v-row(v-else)
        v-col(cols=4 align="left") Automatically sync remotes:
        v-col( align="left")
          v-icon(v-if="instancePost.automatic_update" small color="green") mdi-check-circle
          v-icon(v-if="!instancePost.automatic_update" small) mdi-close-circle
        v-col(v-if="!remote" cols=1 align="center")
          v-btn(@click="edit_automatic_update = !edit_automatic_update" small icon)
            v-icon mdi-pencil
        //- v-col(cols=1 align="center")
      //- Autmoatically execute pending jobs: display mode
      v-row(v-if="edit_automatic_workflow_execution" align="center")
        v-col(cols=4  align="left") Automatically start remote workflows:
        v-col(align="left")
          v-checkbox(v-model="instancePost.automatic_workflow_execution" label="Check automatically for remote updates")
        v-col(cols=1 align="center")
          v-btn(@click="edit_automatic_workflow_execution = !edit_automatic_workflow_execution; updateInstanceForm();" small icon)
            v-icon mdi-content-save
      //- display mode
      v-row(v-else)
        v-col(cols=4 align="left") Automatically start remote workflows:
        v-col( align="left")
          v-icon(v-if="instancePost.automatic_workflow_execution" small color="green") mdi-check-circle
          v-icon(v-if="!instancePost.automatic_workflow_execution" small) mdi-close-circle
        v-col(v-if="!remote" cols=1 align="center")
          v-btn(@click="edit_automatic_workflow_execution = !edit_automatic_workflow_execution" small icon)
            v-icon mdi-pencil
      //- Allowed DAGs: edit mode
      v-row(v-if="edit_allowed_dags" align="center")
        v-col(cols=4 align="left") Allowed DAGs:
        v-col(align="left")
          v-select(v-model='instancePost.allowed_dags' :items='dags' label='Allowed dags' multiple='' chips='' hint='Which dags are allowed to be triggered' persistent-hint='')
          //- span( v-for='dag in instance.allowed_dags') {{dag}}
        v-col(cols=1 align="center")
          v-btn(@click="edit_allowed_dags = !edit_allowed_dags; updateInstanceForm();" small icon)
            v-icon mdi-content-save
      //- display mode
      v-row(v-else)
        v-col(cols=4 align="left") Allowed DAGs:
        v-col(align="left")
          v-chip(v-for='dag in instancePost.allowed_dags' small) {{dag}}
        v-col(v-if="!remote" cols=1 align="center")
          v-btn(@click="edit_allowed_dags = !edit_allowed_dags" small icon)
            v-icon mdi-pencil
      //- Allowed Datasets: edit mode
      v-row(v-if="edit_allowed_datasets" align="center")
        v-col(cols=4 align="left") Allowed Datasets:
        v-col(align="left")
          v-select(v-model='instancePost.allowed_datasets' :items='datasets' label='Allowed datasets' multiple='' chips='' hint='Which datasets are allowed to be used' persistent-hint='')
        v-col(cols=1 align="center")
          v-btn(@click="edit_allowed_datasets = !edit_allowed_datasets; updateInstanceForm();" small icon)
            v-icon mdi-content-save
      //- display mode
      v-row(v-else)
        v-col(cols=4 align="left") Allowed Datasets:
        v-col(align="left")
          v-chip(v-for='dataset in instancePost.allowed_datasets' small) {{dataset}}
        v-col(v-if="!remote" cols=1 align="center")
          v-btn(@click="edit_allowed_datasets = !edit_allowed_datasets" small icon)
            v-icon mdi-pencil
  
</template>
  
  <script>
  
  import kaapanaApiService from "@/common/kaapanaApi.service";
  import {loadDatasets} from "@/common/api.service";
  
  
  export default {
    name: 'KaapanaInstance',
    data: () => ({
      dialogOpen: false,
      dialogDelete: false,
      dags: [],
      datasets: [],
      edit_allowed_dags: false,
      edit_allowed_datasets: false,
      edit_automatic_update: false,
      edit_automatic_workflow_execution: false,
      edit_fernet_encrypted: false,
      edit_port: false,      
      edit_ssl_check: false,
      edit_token: false,
    }),
    props: {
      instance: {
        type: Object,
        required: true
      },
    },
    watch: {
      dialogDelete (val) {
        val || this.closeDelete()
      },
      edit_allowed_dags () {
        this.getDags()
      },
      edit_allowed_datasets () {
        this.getDatasets()
      }
    },
    computed: {
      remote() {
        return this.instance.remote
      },
      instancePost (){
        if (this.instance.fernet_key != "deactivated") {
          this.instance.fernet_encrypted = true
        } else {
          this.instance.fernet_encrypted = false
        }
        if (this.instance.allowed_datasets) {
          this.instance.allowed_datasets = this.instance.allowed_datasets.map(({ name }) => name)
        } else {
          this.instance.allowed_datasets = []
        }
        return JSON.parse(JSON.stringify(this.instance))
      }, 
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
      closeDelete() {
        this.dialogDelete = false
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
          .federatedClientApiPost("/get-dags", {
            instance_names: [this.instance.instance_name],
            kind_of_dags: "all"
          })
          .then((response) => {
            this.dags = response.data;
          })
          .catch((err) => {
            console.log(err);
          });
      },
      getDatasets() {
        loadDatasets().then(_datasetNames => {
          this.datasets = _datasetNames;
        })
      },
      updateInstanceForm() {
        let target_endpoint = "/client-kaapana-instance"
        if (this.remote) {
          target_endpoint = "/remote-kaapana-instance"
        }
        kaapanaApiService
          .federatedClientApiPut(target_endpoint, this.instancePost)
          .then((response) => {
            this.$emit('refreshView')
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
  