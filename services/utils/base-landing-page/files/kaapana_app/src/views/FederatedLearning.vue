<template lang="pug">
.federated-panel
  v-tabs-items(v-model='tab')
    v-tab-item(key='client')
      v-container(text-left)
        v-row(@click="toggleClientPanel()").toggleMouseHand
          v-col(cols="4")
            h1 Client Instance
              i(v-if="openedClientPanel==null").v-icon.notranslate.mdi.mdi-chevron-down.theme--light(aria-hidden='true')
              i(v-if="openedClientPanel==0").v-icon.notranslate.mdi.mdi-chevron-up.theme--light(aria-hidden='true')
          v-col(cols="8" align='right')
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
            workflow-execution(:remote="remote" :instances="[clientInstance]")
            v-btn(v-if="clientInstance" color='orange' @click.stop="checkForRemoteUpdates()" rounded dark ) Check for remote jobs
            v-btn(v-if="!clientInstance" color='orange' @click.stop="clientDialog=true" rounded dark) Add client instance
            //- v-btn(v-if="clientInstance" color='orange' @click="submitWorkflow()" rounded dark) Execute Client Workflow
            v-btn(@click.stop="changeTab(1)" color="primary" rounded dark) Switch to remote instance
        v-row
          v-col(sm="12")
            v-expansion-panels(v-model="openedClientPanel")
              v-expansion-panel(key='instance')
                v-expansion-panel-content
                  KaapanaInstance(v-if="clientInstance" :instance="clientInstance" :remote="clientInstance.remote"  @refreshView="refreshClient()" @ei="editClientInstance")
        job-table(v-if="clientInstance" :jobs="clientJobs" :remote="clientInstance.remote"  @refreshView="refreshClient()")

    v-tab-item(key='remote')
      v-container(text-left)
        v-row(@click="toggleRemotePanel()").toggleMouseHand
          v-col(cols="4")
            h1 Remote Instances
              i(v-if="openedRemotePanel==null").v-icon.notranslate.mdi.mdi-chevron-down.theme--light(aria-hidden='true')
              i(v-if="openedRemotePanel==0").v-icon.notranslate.mdi.mdi-chevron-up.theme--light(aria-hidden='true')
          v-spacer
          v-col(cols="8" align='right')
            workflow-execution(:remote="remote" :instances="remoteInstances")
            v-dialog(v-model='remoteDialog' max-width='600px')
              template(v-slot:activator='{ on, attrs }')
                v-btn(color='orange' v-bind='attrs' v-on='on' rounded dark) Add remote instance
              v-card
                v-form(v-model='remoteValid', ref="remoteForm" lazy-validation)
                  v-card-title
                    span.text-h5 Remote Instance
                  v-card-text
                    v-container
                      v-row
                        v-col(cols='5')
                          v-text-field(v-model='remotePost.node_id' label='Node id' required='' :disabled="remoteUpdate")
                        v-col(cols='5')
                          v-text-field(v-model='remotePost.host' label='Host' required=''  :disabled="remoteUpdate")
                        v-col(cols='2')
                          v-text-field(v-model='remotePost.port' label='Port' type="number" required='')
                        v-col(cols='5')
                          v-text-field(v-model='remotePost.token' label='Token' required='')
                        v-col(cols='5')
                            v-text-field(v-model='remotePost.fernet_key' label='Fernet Key' required='')
                        v-col(cols='2')
                          v-checkbox(v-model="remotePost.ssl_check" label="SSL"  required='')
                  v-card-actions
                    v-spacer
                    v-btn.mr-4(@click='submitRemoteForm')
                      | submit
                    v-btn(@click='resetRemoteForm')
                      | clear
            //- v-btn(color='orange' @click="submitWorkflow()" rounded dark) Execute Remote Workflow
            v-btn(@click.stop="changeTab(0)" color="primary" rounded dark) Switch to client instance
        v-row
          v-col(sm="12")
            v-expansion-panels(v-model="openedRemotePanel")
              v-expansion-panel(key='instances')
                v-expansion-panel-content
                  v-container(fluid='')
                    v-row(dense='')
                      v-col(v-for="instance in remoteInstances" :key='instance.id' cols='6')
                        KaapanaInstance(:instance="instance" :remote="instance.remote" @refreshView="refreshRemote()" @ei="editRemoteInstance")
        job-table(v-if="remoteJobs.length"  :jobs="remoteJobs" remote=true @refreshView="refreshRemote()")
</template>

<script>
import Vue from "vue";
import { mapGetters } from "vuex";
import kaapanaApiService from "@/common/kaapanaApi.service";

import JobTable from "@/components/JobTable.vue";
import KaapanaInstance  from "@/components/KaapanaInstance.vue";
import WorkflowExecution  from "@/components/WorkflowExecution.vue";

export default Vue.extend({
  components: {
    JobTable,
    KaapanaInstance,
    WorkflowExecution
  },
  data: () => ({
    tab: 0,
    polling: 0,
    clientDialog: false,
    clientUpdate: false,
    clientValid: false,
    openedClientPanel: null,
    openedRemotePanel: null,
    remoteValid: false,
    remoteUpdate: false,
    remoteDialog: false,
    dags: [],
    datasets: [],
    remoteJobs: [],
    clientJobs: [],
    clientInstance: {},
    remoteInstances: [],
    clientPost: {
      ssl_check: false,
      automatic_update: false,
      automatic_job_execution: false,
      fernet_encrypted: false,
      allowed_dags: [],
      allowed_datasets: []
    },
    remotePost: {
      ssl_check: false,
      token: '',
      host: '',
      node_id: '',
      port: 443,
      fernet_key: 'deactivated',
    }

  }),
  created() {},
  mounted () {
    // this.getHelmCharts();
    // this.getDags(false);
    this.refreshRemote();
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
    }
  },
  computed: {
    remote () {
      return this.tab !== 0  
    },
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
    toggleRemotePanel() {
      if (this.openedRemotePanel == 0) {
        this.openedRemotePanel = null
      } else {
        this.openedRemotePanel = 0
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
    refreshRemote () {
      this.getRemoteInstances()
      this.getRemoteJobs()
    },
    refreshClient() {
      this.getClientInstance()
      this.getClientJobs()
    },
    changeTab(newTab) {
      console.log(newTab)
      if (newTab == 1) {
        console.log('remote')
        this.refreshRemote()
      }
      else {
        this.refreshClient()
      }
      this.tab = newTab
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
          // this.remoteUpdate = false
          // this.remoteDialog = false
          this.refreshClient();
        })
        .catch((err) => {
          console.log(err);
        });
      } else {
      kaapanaApiService
        .federatedClientApiPut("/client-kaapana-instance", this.clientPost)
        .then((response) => {
          // this.clientUpdate = false
          // this.clientDialog = false
          this.remoteUpdate = false
          this.remoteDialog = false
          this.refreshClient();
        })
        .catch((err) => {
          console.log(err);
        });
      }

    },
    resetRemoteForm () {
      this.$refs.remoteForm.reset()
    },
    submitRemoteForm () {
      if (this.remoteUpdate == false) {
        kaapanaApiService
          .federatedClientApiPost("/remote-kaapana-instance", this.remotePost)
          .then((response) => {
            console.log('getting remote')
            // this.clientUpdate = false
            // this.clientDialog = false
            this.remoteUpdate = false
            this.remoteDialog = false
            this.refreshRemote()
          })
          .catch((err) => {
            console.log(err);
          });
      } else {
        kaapanaApiService
          .federatedClientApiPut("/remote-kaapana-instance", this.remotePost)
          .then((response) => {
            // this.clientUpdate = false
            // this.clientDialog = false
            this.remoteUpdate = false
            this.remoteDialog = false
            this.refreshRemote()
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
        .federatedClientApiGet("/datasets")
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
    editRemoteInstance(instance) {
      this.remotePost = instance
      this.remoteDialog = true
      this.remoteUpdate = true
    },
    getClientInstance() {
      kaapanaApiService
        .federatedClientApiGet("/client-kaapana-instance")
        .then((response) => {
          this.clientInstance = response.data;
        })
        .catch((err) => {
          this.clientInstance = {}
        });
    },
    deleteRemoteInstances() {
      kaapanaApiService
        .federatedClientApiDelete("/remote-kaapana-instances")
        .then((response) => {

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
        })
        .catch((err) => {
          console.log(err);
        });
    },
    getRemoteJobs() {
      kaapanaApiService
        .federatedRemoteApiGet("/jobs")
        .then((response) => {
          this.remoteJobs = response.data;
        })
        .catch((err) => {
          console.log(err);
        });
    },
    getClientJobs() {
      kaapanaApiService
        .federatedClientApiGet("/jobs")
        .then((response) => {
          this.clientJobs = response.data;
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
        console.log(this.remote)
        if (this.remote == true){
          console.log('getting remote')
          this.refreshRemote()
        } else {
          console.log('getting client')
          this.refreshClient();
        }
      }, 5000);
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
