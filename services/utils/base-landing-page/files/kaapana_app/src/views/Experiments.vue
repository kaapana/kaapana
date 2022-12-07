<template lang="pug">
  .federated-panel
    v-container(text-left)
      h1 Experiment Management System
      v-row(@click="toggleClientPanel()").toggleMouseHand
        v-col
          h2 Local Instance Profile
            i(v-if="openedClientPanel==null").v-icon.notranslate.mdi.mdi-chevron-down.theme--light(aria-hidden='true')
            i(v-if="openedClientPanel==0").v-icon.notranslate.mdi.mdi-chevron-up.theme--light(aria-hidden='true')
        v-col
          v-dialog(v-model='clientDialog' max-width='600px')
            v-card
              v-form(v-model='clientValid' ref="clientForm" lazy-validation)
                v-card-title
                  span.text-h5 Client Instance
                v-card-text
                  v-container
                    v-row
                      v-col(cols='12')
                        v-select(v-model='clientPost.allowed_dags' :items='dags' label='Allowed dags' multiple='' chips='' hint='Which dags are allowed to be triggered' persistent-hint='')
                      v-col(cols='12')
                        v-select(v-model='clientPost.allowed_datasets' :items='datasets' label='Allowed datasets' multiple='' chips='' hint='Which datasets are allowed to be triggered' persistent-hint='')
                      v-col(cols='8')
                        v-checkbox(v-model="clientPost.automatic_update" label="Check automatically for remote updates")
                      v-col(cols='4')
                        v-checkbox(v-model="clientPost.ssl_check" label="SSL"  required='')
                      v-col(cols='8')
                        v-checkbox(v-model="clientPost.automatic_job_execution" label="Execute automatically jobs")
                      v-col(cols='4')
                        v-checkbox(v-model="clientPost.fernet_encrypted" label="Fernet encrypted"  required='')
                v-card-actions
                  v-spacer
                  v-btn.mr-4(@click='submitClientForm')
                    | submit
                  v-btn(@click='resetClientForm')
                    | clear
        v-col
          workflow-execution(ref="workflowexecution" v-if="clientInstance" :remote='true' :instances="allInstances" :clientinstance="clientInstance" @refreshView="refreshClient()")
        v-col
          add-remote-instance(ref="addremoteinstance" :remote='true')
          view-remote-instances(ref="viewremoteinstances" :clientinstance="clientInstance" :remote='true')
          v-btn(v-if="clientInstance" color='primary' @click.stop="checkForRemoteUpdates()" dark ) Sync remote
          v-btn(v-if="!clientInstance" color='primary' @click.stop="clientDialog=true" dark) Add client instance
      v-row
        v-col(sm="12")
          v-expansion-panels(v-model="openedClientPanel")
            v-expansion-panel(key='instance')
              v-expansion-panel-content
                KaapanaInstance(v-if="clientInstance" :instance="clientInstance" :remote="clientInstance.remote"  @refreshView="refreshClient()" @ei="editClientInstance")
      //- job-table(v-if="clientInstance" :experiments="clientExperiments" :jobs="clientJobs" :remote="clientInstance.remote"  @refreshView="refreshClient()")
      experiment-table(v-if="clientInstance" :instance="clientInstance" :experiments="clientExperiments" :remote="clientInstance.remote" @refreshView="refreshClient()")
  </template>

<script>
import Vue from "vue";
import { mapGetters } from "vuex";
import kaapanaApiService from "@/common/kaapanaApi.service";

// import JobTable from "@/components/JobTable.vue";
import ExperimentTable from "@/components/ExperimentTable.vue"
import KaapanaInstance  from "@/components/KaapanaInstance.vue";
import WorkflowExecution  from "@/components/WorkflowExecution.vue";
import AddRemoteInstance from "@/components/AddRemoteInstance.vue";
import ViewRemoteInstances from "@/components/ViewRemoteInstances.vue";

export default Vue.extend({
  components: {
    // JobTable,
    ExperimentTable,
    KaapanaInstance,
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
    toggleClientPanel() {
      if (this.openedClientPanel == 0) {
        this.openedClientPanel = null
      } else {
        this.openedClientPanel = 0
      }
    },
    checkForRemoteUpdates() {
      console.log('checking remote')
      kaapanaApiService
        .federatedClientApiGet("/check-for-remote-updates")
        .then((response) => {
          this.$emit('refreshView')
        })
        .catch((err) => {
          console.log(err);
        });
    },
    refreshClient() {
      // console.log("refreshClient() in Experiment.vue")
      this.getClientInstance()
      this.getClientExperiments()
      this.getClientJobs()
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
            console.log("all_instance_names: ", this.all_instance_names, "clientInstance.instance_name: ", this.clientInstance.instance_name)
            this.allInstances.push(this.clientInstance)
            this.all_instance_names.push(this.clientInstance.instance_name)
          }
          console.log("clientInstance: ", this.clientInstance);
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
          // console.log(this.clientExperiments)
        })
        .catch((err) => {
          console.log(err);
        });
    },
    getClientJobs() {
      kaapanaApiService
        .federatedClientApiGet("/jobs",{
        limit: 100,
        }).then((response) => {
          this.clientJobs = response.data;
          // console.log(this.clientJobs)
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
          console.log("remoteInstances: ", this.remoteInstances)
          this.remoteInstances.forEach(remote_instance => {
            if (this.all_instance_names.indexOf(remote_instance.instance_name) === -1) {
              console.log("all_instance_names: ", this.all_instance_names, "remote_instance.instance_name: ", remote_instance.instance_name)
              this.allInstances.push(remote_instance)
              this.all_instance_names.push(remote_instance.instance_name)
            }
          })
          console.log("allInstances: ", this.allInstances)
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
</style>
