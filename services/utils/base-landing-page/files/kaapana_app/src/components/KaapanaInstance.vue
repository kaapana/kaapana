
<template lang="pug">
  v-card
    v-card-title Node ID: {{ instance.node_id }}
    v-card-text
      div Network: {{ instance.protocol }}://{{ instance.host }}:{{ instance.port }}
      div Fernet key: {{ instance.fernet_key }}
      div Token: {{ instance.token }}
      div SSL: {{ instance.ssl_check }}
      div Sync remote jobs: {{ instance.automatic_update }}
      div Autmoatically execute pending jobs: {{ instance.automatic_job_execution }}
      div Created: {{ instance.time_created }}
      div Updated: {{ instance.time_updated }}
      div Allowed dags: 
        span( v-for='dag in instance.allowed_dags') {{dag}} 
      div Allowed datasets: 
        span( v-for='dataset in instance.allowed_datasets') {{dataset}} 
    v-card-actions
      v-btn(color='orange' @click="editInstance()" rounded dark) Edit Instance
      v-btn(color='orange' @click="deleteInstance()" rounded dark) Delete instance    
      v-btn(v-if="remote==false" color='orange' dark='' @click="checkForRemoteUpdates()" rounded) Check for remote jobs

    v-dialog(v-model='dialogDelete' max-width='500px')
      v-card
        v-card-title.text-h5 Are you sure you want to delete this instance. With it all corresponding jobs are deleted?
        v-card-actions
          v-spacer
          v-btn(color='blue darken-1' text='' @click='closeDelete') Cancel
          v-btn(color='blue darken-1' text='' @click='deleteInstanceConfirm') OK
          v-spacer
</template>

<script lang="ts">

import kaapanaApiService from "@/common/kaapanaApi.service";

export default {
  name: 'KaapanaInstance',
  data: () => ({
    dialogDelete: false,
  }),
  props: {
    instance: {
      type: Object,
      required: true
    },
    remote: {
      type: Boolean,
      required: true
    }
  },
  // watch: {
  //   dialog (val) {
  //     val || this.close()
  //   },
  //   dialogDelete (val) {
  //     val || this.closeDelete()
  //   },
  //   },
  methods:{
    checkForRemoteUpdates() {
      kaapanaApiService
        .federatedClientApiGet("/check-for-remote-updates")
        .then((response: any) => {
          this.$emit('refreshView')
    	    // this.$emit('gci')
        })
        .catch((err: any) => {
          console.log(err);
        });
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
        .then((response: any) => {
          this.$emit('refreshView')
          this.closeDelete()
        })
        .catch((err: any) => {
          console.log(err);
        });
      // if (this.remote == true){
    	//   this.$emit('gris')
    	//   this.$emit('grj')
      // } else {
    	//   this.$emit('gci')
      // }
    },
    deleteInstance() {
      this.dialogDelete = true
    },
  }
}
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped lang="scss">


</style>
