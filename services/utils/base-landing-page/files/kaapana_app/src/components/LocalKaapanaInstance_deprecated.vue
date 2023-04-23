
<template lang="pug">
  v-card(class="my-auto")
    v-card-title Local Instance: {{ instance.instance_name }}
    v-card-text(class=text-primary)
      v-row
        v-col(cols=4 align="left")
          v-row(align="start")
            v-col(align="left") Network: 
            v-col(align="left") {{ instance.protocol }}://{{ instance.host }}:{{ instance.port }}
            //- v-col(cols=1)
          v-row(align="start")
            v-col(align="left") Token: 
            v-col(align="left") {{ instance.token }}
            //- v-col(cols=1)
          v-row 
            v-col(align="left") Created: 
            v-col(align="left") {{ instance.time_created }}
            //- v-col(cols=1)
          v-row 
            v-col(align="left") Updated: 
            v-col(align="left") {{ instance.time_updated }}
            //- v-col(cols=1)
        v-divider(vertical)
        v-col(cols=4 align="left")
          //- SSL: edit mode
          v-row(v-if="edit_ssl_check" align="center")
            v-col(align="left") SSL:
            v-col(align="left")
              v-checkbox(v-model="clientPost.ssl_check" label="SSL"  required='')
            v-col(cols=1 align="left")
              v-btn(@click="edit_ssl_check = !edit_ssl_check; updateClientForm();" small icon)
                v-icon mdi-content-save
          //- display mode
          v-row(v-else)
            v-col(align="left") SSL:
            v-col(align="left")
              v-icon(v-if="clientPost.ssl_check" small color="green") mdi-check-circle
              v-icon(v-if="!clientPost.ssl_check" small) mdi-close-circle
            v-col(cols=1 align="left")
              v-btn(@click="edit_ssl_check = !edit_ssl_check" small icon)
                v-icon mdi-pencil        
          //- Fernet key: edit mode
          v-row(v-if="edit_fernet_encrypted" align="center")
            v-col(align="left") Fernet key:
            v-col(align="left")
              v-checkbox(v-model="clientPost.fernet_encrypted" label="Fernet encrypted"  required='')
            v-col(cols=1 align="left")
              v-btn(@click="edit_fernet_encrypted = !edit_fernet_encrypted; updateClientForm();" small icon)
                v-icon mdi-content-save
          //- display mode
          v-row(v-else)
            v-col(align="left") Fernet key:
            v-col(align="left")
              div {{ clientPost.fernet_key }}
            v-col(cols=1 align="left")
              v-btn(@click="edit_fernet_encrypted = !edit_fernet_encrypted" small icon)
                v-icon mdi-pencil
          //- Sync remote: edit mode
          v-row(v-if="edit_automatic_update" align="center")
            v-col(align="left") Automatically sync remotes:
            v-col(align="left")
              v-checkbox(v-model="clientPost.automatic_update" label="Check automatically for remote updates")
            v-col(cols=1 align="left")
              v-btn(@click="edit_automatic_update = !edit_automatic_update; updateClientForm();" small icon)
                v-icon mdi-content-save
          //- display mode
          v-row(v-else)
            v-col(align="left") Automatically sync remotes:
            v-col(align="left")
              v-icon(v-if="clientPost.automatic_update" small color="green") mdi-check-circle
              v-icon(v-if="!clientPost.automatic_update" small) mdi-close-circle
            v-col(cols=1 align="left")
              v-btn(@click="edit_automatic_update = !edit_automatic_update" small icon)
                v-icon mdi-pencil
          //- Autmoatically execute pending jobs: edit mode
          v-row(v-if="edit_automatic_exp_execution" align="center")
            v-col(align="left") Automatically start remote experiments:
            v-col(align="left")
              v-checkbox(v-model="clientPost.automatic_exp_execution" label="Start automatically remote experiments")
            v-col(cols=1 align="left")
              v-btn(@click="edit_automatic_exp_execution = !edit_automatic_exp_execution; updateClientForm();" small icon)
                v-icon mdi-content-save
          //- display mode
          v-row(v-else)
            v-col(align="left") Automatically start remote experiments:
            v-col(align="left")
              v-icon(v-if="clientPost.automatic_exp_execution" small color="green") mdi-check-circle
              v-icon(v-if="!clientPost.automatic_exp_execution" small) mdi-close-circle
            v-col(cols=1 align="left")
              v-btn(@click="edit_automatic_exp_execution = !edit_automatic_exp_execution" small icon)
                v-icon mdi-pencil
        v-divider(vertical)
        v-col(cols=4 align="left")
          //- Allowed DAGs: edit mode
          v-row(v-if="edit_allowed_dags" align="center")
            v-col(align="left") Allowed DAGs:
            v-col(align="left")
              v-select(v-model='clientPost.allowed_dags' :items='dags' label='Allowed dags' multiple='' chips='' hint='Which dags are allowed to be triggered' persistent-hint='')
              //- span( v-for='dag in instance.allowed_dags') {{dag}}
            v-col(cols=1 align="left")
              v-btn(@click="edit_allowed_dags = !edit_allowed_dags; updateClientForm();" small icon)
                v-icon mdi-content-save
          //- display mode
          v-row(v-else)
            v-col(align="left") Allowed DAGs:
            v-col(align="left")
              v-chip(v-for='dag in clientPost.allowed_dags' small) {{dag}}
            v-col(cols=1 align="left")
              v-btn(@click="edit_allowed_dags = !edit_allowed_dags" small icon)
                v-icon mdi-pencil
          //- Allowed Datasets: edit mode
          v-row(v-if="edit_allowed_datasets" align="center")
            v-col(align="left") Allowed Datasets:
            v-col(align="left")
              v-select(v-model='clientPost.allowed_datasets' :items='datasets' label='Allowed datasets' multiple='' chips='' hint='Which datasets are allowed to be used' persistent-hint='')
            v-col(cols=1 align="left")
              v-btn(@click="edit_allowed_datasets = !edit_allowed_datasets; updateClientForm();" small icon)
                v-icon mdi-content-save
          //- display mode
          v-row(v-else)
            v-col(align="left") Allowed Datasets:
            v-col(align="left")
              v-chip(v-for='dataset in clientPost.allowed_datasets' small) {{dataset}}
            v-col(cols=1 align="left")
              v-btn(@click="edit_allowed_datasets = !edit_allowed_datasets" small icon)
                v-icon mdi-pencil
    v-card-actions
      //- v-btn(color='red' @click="deleteInstance()" small icon)
      //-   v-icon(color="red" dark) mdi-trash-can-outline
  
    //- v-dialog(v-model='dialogDelete' max-width='500px')
    //-   v-card
    //-     v-card-title.text-h5 Are you sure you want to delete this instance. With it all corresponding jobs and experiments are deleted?
    //-     v-card-actions
    //-       v-spacer
    //-       v-btn(color='blue darken-1' text='' @click='closeDelete') Cancel
    //-       v-btn(color='blue darken-1' text='' @click='deleteInstanceConfirm') OK
    //-       v-spacer
  
</template>
  
  <script>
  
  import kaapanaApiService from "@/common/kaapanaApi.service";
  import {loadDatasetNames} from "@/common/api.service";
  
  
  export default {
    name: 'LocalKaapanaInstance',
    data: () => ({
      dags: [],
      datasets: [],
      clientPost: {
        ssl_check: false,
        automatic_update: false,
        automatic_exp_execution: false,
        fernet_encrypted: false,
        allowed_dags: [],
        allowed_datasets: []
      },
      edit_ssl_check: false,
      edit_automatic_update: false,
      edit_automatic_exp_execution: false,
      edit_fernet_encrypted: false,
      edit_allowed_dags: false,
      edit_allowed_datasets: false,
    }),
    props: {
      instance: {
        type: Object,
        required: true
      },
      // remote: { // false for client instance; true for remote instances
      //   type: Boolean,
      //   required: true
      // },
    },
    mounted () {
      console.log("Starting up Component LocalKaapanaInstance!")
      console.log("Got ClientInstance: ", this.instance)
      this.getDags();
      this.getDatasets();
    },
    watch: {
      instance () {
        this.clientPost = this.instance
        this.clientPost.fernet_encrypted = false
        console.log('Getting Dags and Datasets')
        console.log("this.clientPost:", this.clientPost)
      },
      // dialogDelete (val) {
      //   val || this.closeDelete()
      // },
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
    },
    methods:{
      // closeDelete() {
      //   this.dialogDelete = false
      // },
      // deleteInstanceConfirm () {
      //   let params = {
      //     kaapana_instance_id: this.instance.id,
      //   };
      //   kaapanaApiService
      //     .federatedClientApiDelete("/kaapana-instance", params)
      //     .then((response) => {
      //       this.$emit('refreshView')
      //       this.closeDelete()
      //     })
      //     .catch((err) => {
      //       console.log(err);
      //     });
      // },
      // deleteInstance() {
      //   this.dialogDelete = true
      // },
      getDags() {
        kaapanaApiService
          .federatedClientApiPost("/get-dags", {
            instance_names: [this.instance.instance_name]
          })
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
      updateClientForm() {
        kaapanaApiService
          .federatedClientApiPut("/client-kaapana-instance", this.clientPost)
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
  .center-text {
    display: flex;
    justify-content: center;
    align-items: center;
  }
  
  </style>
  