<template>
  <v-container text-left fluid>
    <!-- workflow-execution 
      ref="workflowexecution"
      v-if="clientInstance" 
      :remote="true" 
      :instances="allInstances"
      :clientinstance="clientInstance" 
      @refreshView="refreshClient()"
    ></workflow-execution -->
    <workflow-execution></workflow-execution>
  </v-container>
</template>

<script>
import Vue from "vue";
import { mapGetters } from "vuex";
import kaapanaApiService from "@/common/kaapanaApi.service";

import WorkflowExecution  from "@/components/WorkflowExecution.vue";


export default Vue.extend({
  components: {
    WorkflowExecution,
  },
  data: () => ({
    // clientInstance: {},
    // allInstances: [],
  }),
  created() {
  },
  mounted () {console.log("Hello, I am the Experiment Execution View!")
  },
  watch: {
  },
  // computed: {
  //   ...mapGetters(['currentUser', 'isAuthenticated'])
  // },
  methods: {
    // refreshClient() {
    //   this.getClientInstance()
    //   this.getRemoteInstances()
    // },
    // getDags() {
    //   kaapanaApiService
    //     .federatedClientApiPost("/get-dags", {remote: false})
    //     .then((response) => {
    //       this.dags = response.data;
    //       console.log("Fetched DAGs: ", this.dags);
    //     })
    //     .catch((err) => {
    //       console.log(err);
    //     });
    // },
    // getDatasets() {
    //   kaapanaApiService
    //     .federatedClientApiGet("/cohort-names")
    //     .then((response) => {
    //       this.datasets = response.data;
    //     })
    //     .catch((err) => {
    //       console.log(err);
    //     });
    // },
    // getClientInstance() {
    //   kaapanaApiService
    //     .federatedClientApiGet("/client-kaapana-instance")
    //     .then((response) => {
    //       this.clientInstance = response.data;
    //       if (this.all_instance_names.indexOf(this.clientInstance.instance_name) === -1) {
    //         this.allInstances.push(this.clientInstance)
    //         this.all_instance_names.push(this.clientInstance.instance_name)
    //       }
    //       console.log("clientInstance: ", this.clientInstance);
    //     })
    //     .catch((err) => {
    //       this.clientInstance = {}
    //     });
    // },
    
    // getRemoteInstances() {
    //   kaapanaApiService
    //     .federatedClientApiPost("/get-remote-kaapana-instances")
    //     .then((response) => {
    //       this.remoteInstances = response.data;
    //       this.remoteInstances.forEach(remote_instance => {
    //         if (this.all_instance_names.indexOf(remote_instance.instance_name) === -1) {
    //           this.allInstances.push(remote_instance)
    //           this.all_instance_names.push(remote_instance.instance_name)
    //         }
    //       })
    //     })
    //     .catch((err) => {
    //       console.log(err);
    //     });
    // },
    // clearExtensionsInterval() {
    //   window.clearInterval(this.polling);
    // },
    // startExtensionsInterval() {
    //   this.polling = window.setInterval(() => {
    //     // a little bit ugly... https://stackoverflow.com/questions/40410332/vuejs-access-child-components-data-from-parent
    //     if (!this.$refs.workflowexecution.dialogOpen) {
    //       this.refreshClient();
    //     }
    //   }, 15000);
    // }
  },
});
</script>

<style lang="scss">

</style>
