<template lang="pug">
  .federated-panel
    v-container(text-left fluid)
      v-row
        v-col(cols="9", align="left")
          experiment-table(v-if="clientInstance" :instance="clientInstance" :experiments="clientExperiments" :remote="clientInstance.remote" @refreshView="refreshClient()")
        v-col(cols="3", align="right")
          v-container(fluid)
            v-row(class="someSpace" justify="center" align="center")
              workflow-execution(ref="workflowexecution" v-if="clientInstance" :remote='true' :instances="allInstances" :clientinstance="clientInstance" @refreshView="refreshClient()")
            v-row(class="someSpace" justify="center" align="center")
              LocalKaapanaInstance(v-if="clientInstance" :instance="clientInstance" :remote="false"  @refreshView="refreshClient()" @ei="editClientInstance")
            v-row(class="someSpace" justify="center" align="center")
              v-spacer
              h2 REMOTE INSTANCES
              v-spacer
              add-remote-instance(ref="addremoteinstance" :remote='true')
              v-spacer
              view-remote-instances(ref="viewremoteinstances" :clientinstance="clientInstance" :remote='true')
              v-spacer
              v-btn(v-if="clientInstance" @click.stop="checkForRemoteUpdates()" small icon)
                v-icon(color='primary' dark x-large) mdi-sync-circle
              v-spacer
              v-btn(v-if="!clientInstance" color='primary' @click.stop="clientDialog=true" dark) Add client instance  
</template>

<script>
import Vue from "vue";
import { mapGetters } from "vuex";
import kaapanaApiService from "@/common/kaapanaApi.service";

import ExperimentTable from "@/components/ExperimentTable.vue"
import KaapanaInstance  from "@/components/KaapanaInstance.vue";
import LocalKaapanaInstance from "@/components/LocalKaapanaInstance.vue";
import WorkflowExecution  from "@/components/WorkflowExecution.vue";
import AddRemoteInstance from "@/components/AddRemoteInstance.vue";
import ViewRemoteInstances from "@/components/ViewRemoteInstances.vue";
import {loadDatasetNames} from "@/common/api.service";

export default Vue.extend({
  components: {
    ExperimentTable,
    KaapanaInstance,
    LocalKaapanaInstance,
    WorkflowExecution,
    AddRemoteInstance,
    ViewRemoteInstances
  },
  data: () => ({
    polling: 0,
    clientDialog: false,
    clientUpdate: false,
    clientValid: false,
    openedClientPanel: null,
    dags: [],
    datasets: [],
    clientJobs: [],
    clientExperiments: [],
    clientInstance: {},
    remoteInstances: [],
    allInstances: [],
    all_instance_names: [],
    clientPost: {
      ssl_check: false,
      automatic_update: false,
      automatic_job_execution: false,
      fernet_encrypted: false,
      allowed_dags: [],
      allowed_datasets: []
    }
  }),
  created() {},
  mounted () {
    this.refreshClient();
    this.startExtensionsInterval()
  },
  watch: {
    clientDialog: function (val) {
      if (val == true) {
        this.getDags();
        this.getDatasets();
        console.log('Getting Dags and Datasets')
      }
    },
  },
  computed: {
    ...mapGetters(['currentUser', 'isAuthenticated'])
  },
  methods: {
    checkForRemoteUpdates() {
      console.log('checking remote')
      kaapanaApiService
        .federatedClientApiGet("/check-for-remote-updates")
        .then((response) => {
          this.$notify({
            type: 'success',
            title: 'Successfully checked for remote updates',
            // text: 
          })
          this.$emit('refreshView')
        })
        .catch((err) => {
          console.log(err);
        });
    },
    refreshClient() {
      this.getClientInstance()
      this.getClientExperiments()
      // this.getClientJobs()
      this.getRemoteInstances()
    },
    resetClientForm () {
      this.$refs.clientForm.reset()
    },
    submitClientForm () {
      if (this.clientUpdate == false) {
      kaapanaApiService
        .federatedClientApiPost("/client-kaapana-instance", this.clientPost)
        .then((response) => {
          this.clientUpdate = false
          this.clientDialog = false
          this.refreshClient();
        })
        .catch((err) => {
          console.log(err);
        });
      } else {
      kaapanaApiService
        .federatedClientApiPut("/client-kaapana-instance", this.clientPost)
        .then((response) => {
          this.clientUpdate = false
          this.clientDialog = false
          get_remote_updates
        })
        .catch((err) => {
          console.log(err);
        });
      }
    },
    getDags() {
      kaapanaApiService
        .federatedClientApiPost("/get-dags", {remote: false})
        .then((response) => {
          this.dags = response.data;
          console.log("Fetched DAGs: ", this.dags);
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
    editClientInstance(instance) {
      this.clientPost = instance
      this.clientPost.fernet_encrypted = false
      this.clientDialog = true
      this.clientUpdate = true
    },
    getClientInstance() {
      kaapanaApiService
        .federatedClientApiGet("/client-kaapana-instance")
        .then((response) => {
          this.clientInstance = response.data;
          if (this.all_instance_names.indexOf(this.clientInstance.instance_name) === -1) {
            this.allInstances.push(this.clientInstance)
            this.all_instance_names.push(this.clientInstance.instance_name)
          }
          // console.log("clientInstance: ", this.clientInstance);
        })
        .catch((err) => {
          this.clientInstance = {}
        });
    },
    getClientExperiments() {
      kaapanaApiService
        .federatedClientApiGet("/experiments",{
        limit: 100,
        }).then((response) => {
          this.clientExperiments = response.data;
          // console.log("clientExperiments: ", this.clientExperiments)
        })
        .catch((err) => {
          console.log(err);
        });
    },
    getRemoteInstances() {
      kaapanaApiService
        .federatedClientApiPost("/get-remote-kaapana-instances")
        .then((response) => {
          this.remoteInstances = response.data;
          this.remoteInstances.forEach(remote_instance => {
            if (this.all_instance_names.indexOf(remote_instance.instance_name) === -1) {
              this.allInstances.push(remote_instance)
              this.all_instance_names.push(remote_instance.instance_name)
            }
          })
        })
        .catch((err) => {
          console.log(err);
        });
    },
    clearExtensionsInterval() {
      window.clearInterval(this.polling);
    },
    startExtensionsInterval() {
      this.polling = window.setInterval(() => {
        // a little bit ugly... https://stackoverflow.com/questions/40410332/vuejs-access-child-components-data-from-parent
        if (!this.$refs.workflowexecution.dialogOpen) {
          this.refreshClient();
        }
      }, 15000);
    }
  },
  beforeDestroy() {
    this.clearExtensionsInterval()
  },
});
</script>

<style lang="scss">
a {
  text-decoration: none;
}
.v-expansion-panel-content__wrap {
  padding: 0;
}
.toggleMouseHand {
  cursor: pointer;
}
.someSpace {
  margin-bottom: 20px; /* add horizontal space between items */
}
</style>
