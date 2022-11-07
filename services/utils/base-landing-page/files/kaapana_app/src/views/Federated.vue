<template lang="pug">
.federated-panel
  v-container(text-left)
    v-row(@click="toggleRemotePanel()").toggleMouseHand
      v-col(cols="4")
        h1 Remote Instances
          i(v-if="openedRemotePanel==null").v-icon.notranslate.mdi.mdi-chevron-down.theme--light(aria-hidden='true')
          i(v-if="openedRemotePanel==0").v-icon.notranslate.mdi.mdi-chevron-up.theme--light(aria-hidden='true')
      v-spacer
      v-col(cols="8" align='right')
        workflow-execution(ref="workflowexecution" :remote='true' :instances="remoteInstances")
        v-dialog(v-model='remoteDialog' max-width='600px')
          v-card
            v-form(v-model='remoteValid', ref="remoteForm" lazy-validation)
              v-card-title
                span.text-h5 Remote Instance
              v-card-text
                v-container
                  v-row
                    v-col(cols='5')
                      v-text-field(v-model='remotePost.instance_name' label='Instance name' required='' :disabled="remoteUpdate")
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
        v-btn(color='orange' @click.stop="openRemoteDialog" rounded dark) Add remote instance
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
    polling: 0,
    openedRemotePanel: null,
    remoteValid: false,
    remoteUpdate: false,
    remoteDialog: false,
    remoteJobs: [],
    remoteInstances: [],
    remotePost: {
      ssl_check: false,
      token: '',
      host: '',
      instance_name: '',
      port: 443,
      fernet_key: 'deactivated',
    }
  }),
  created() {},
  mounted () {
    this.refreshRemote();
    this.startExtensionsInterval()
  },
  computed: {
    ...mapGetters(['currentUser', 'isAuthenticated'])
  },
  methods: {
    toggleRemotePanel() {
      if (this.openedRemotePanel == 0) {
        this.openedRemotePanel = null
      } else {
        this.openedRemotePanel = 0
      }
    },
    refreshRemote () {
      this.getRemoteInstances()
      this.getRemoteJobs()
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
            this.remoteUpdate = false
            this.remoteDialog = false
            this.refreshRemote()
          })
          .catch((err) => {
            console.log(err);
          });
      }
    },
    editRemoteInstance(instance) {
      this.remotePost = instance
      this.remoteDialog = true
      this.remoteUpdate = true
    },
    openRemoteDialog() {
      this.remoteDialog = true
      this.remoteUpdate = false
      this.remotePost = {
        ssl_check: false,
        token: '',
        host: '',
        instance_name: '',
        port: 443,
        fernet_key: 'deactivated',
      }
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
        .federatedRemoteApiGet("/jobs", {
        limit: 100,
        }).then((response) => {
          this.remoteJobs = response.data;
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
        if (!this.$refs.workflowexecution.dialogOpen) {
          this.refreshRemote();
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
