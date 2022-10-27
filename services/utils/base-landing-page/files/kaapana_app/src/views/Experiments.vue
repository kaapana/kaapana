<template lang="pug">
.federated-panel
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
        workflow-execution(ref="workflowexecution" v-if="clientInstance" :remote='false', :instances="[clientInstance]")
        v-btn(v-if="clientInstance" color='orange' @click.stop="checkForRemoteUpdates()" rounded dark ) Sync remote
        v-btn(v-if="!clientInstance" color='orange' @click.stop="clientDialog=true" rounded dark) Add client instance
        //- v-btn(v-if="clientInstance" color='orange' @click="submitWorkflow()" rounded dark) Execute Client Workflow
    v-row
      v-col(sm="12")
        v-expansion-panels(v-model="openedClientPanel")
          v-expansion-panel(key='instance')
            v-expansion-panel-content
              KaapanaInstance(v-if="clientInstance" :instance="clientInstance" :remote="clientInstance.remote"  @refreshView="refreshClient()" @ei="editClientInstance")
    job-table(v-if="clientInstance" :jobs="clientJobs" :remote="clientInstance.remote"  @refreshView="refreshClient()")
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
    polling: 0,
    clientDialog: false,
    clientUpdate: false,
    clientValid: false,
    openedClientPanel: null,
    // openedRemotePanel: null,
    // remoteValid: false,
    // remoteUpdate: false,
    // remoteDialog: false,
    dags: [],
    datasets: [],
    // remoteJobs: [],
    clientJobs: [],
    clientInstance: {},
    // remoteInstances: [],
    clientPost: {
      ssl_check: false,
      automatic_update: false,
      automatic_job_execution: false,
      fernet_encrypted: false,
      allowed_dags: [],
      allowed_datasets: []
    },
    // remotePost: {
    //   ssl_check: false,
    //   token: '',
    //   host: '',
    //   instance_name: '',
    //   port: 443,
    //   fernet_key: 'deactivated',
    // }
  }),
  created() {},
  mounted () {
    // this.refreshRemote();
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
    // toggleRemotePanel() {
    //   if (this.openedRemotePanel == 0) {
    //     this.openedRemotePanel = null
    //   } else {
    //     this.openedRemotePanel = 0
    //   }
    // },
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
    // refreshRemote () {
    //   this.getRemoteInstances()
    //   this.getRemoteJobs()
    // },
    refreshClient() {
      this.getClientInstance()
      this.getClientJobs()
    },
    // changeTab(newTab) {
    //   console.log(newTab)
    //   if (newTab == 1) {
    //     console.log('remote')
    //     this.refreshRemote()
    //   }
    //   else {
    //     this.refreshClient()
    //   }
    //   this.tab = newTab
    // },
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
          this.refreshClient();
        })
        .catch((err) => {
          console.log(err);
        });
      }

    },
    // resetRemoteForm () {
    //   this.$refs.remoteForm.reset()
    // },
    // submitRemoteForm () {
    //   if (this.remoteUpdate == false) {
    //     kaapanaApiService
    //       .federatedClientApiPost("/remote-kaapana-instance", this.remotePost)
    //       .then((response) => {
    //         console.log('getting remote')
    //         this.remoteUpdate = false
    //         this.remoteDialog = false
    //         this.refreshRemote()
    //       })
    //       .catch((err) => {
    //         console.log(err);
    //       });
    //   } else {
    //     kaapanaApiService
    //       .federatedClientApiPut("/remote-kaapana-instance", this.remotePost)
    //       .then((response) => {
    //         this.remoteUpdate = false
    //         this.remoteDialog = false
    //         this.refreshRemote()
    //       })
    //       .catch((err) => {
    //         console.log(err);
    //       });
    //   }
    // },
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
    // editRemoteInstance(instance) {
    //   this.remotePost = instance
    //   this.remoteDialog = true
    //   this.remoteUpdate = true
    // },
    // openRemoteDialog() {
    //   this.remoteDialog = true
    //   this.remoteUpdate = false
    //   this.remotePost = {
    //     ssl_check: false,
    //     token: '',
    //     host: '',
    //     instance_name: '',
    //     port: 443,
    //     fernet_key: 'deactivated',
    //   }
    // },
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
    // deleteRemoteInstances() {
    //   kaapanaApiService
    //     .federatedClientApiDelete("/remote-kaapana-instances")
    //     .then((response) => {

    //     })
    //     .catch((err) => {
    //       console.log(err);
    //     });
    // },
    // getRemoteInstances() {
    //   kaapanaApiService
    //     .federatedClientApiPost("/get-remote-kaapana-instances")
    //     .then((response) => {
    //       this.remoteInstances = response.data;
    //     })
    //     .catch((err) => {
    //       console.log(err);
    //     });
    // },
    // getRemoteJobs() {
    //   kaapanaApiService
    //     .federatedRemoteApiGet("/jobs", {
    //     limit: 100,
    //     }).then((response) => {
    //       this.remoteJobs = response.data;
    //     })
    //     .catch((err) => {
    //       console.log(err);
    //     });
    // },
    getClientJobs() {
      kaapanaApiService
        .federatedClientApiGet("/jobs",{
        limit: 100,
        }).then((response) => {
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
