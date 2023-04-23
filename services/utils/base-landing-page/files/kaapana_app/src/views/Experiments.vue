<template lang="pug">
  .federated-panel
    v-container(text-left fluid)
      experiment-table(v-if="clientInstance" :instance="clientInstance" :allInstances="allInstances" :experiments="clientExperiments" @refreshView="refreshClient()")

</template>

<script>
import Vue from "vue";
import { mapGetters } from "vuex";
import kaapanaApiService from "@/common/kaapanaApi.service";

import ExperimentTable from "@/components/ExperimentTable.vue"
import {loadDatasetNames} from "@/common/api.service";

export default Vue.extend({
  components: {
    ExperimentTable,
  },
  data: () => ({
    polling: 0,
    clientExperiments: [],
    clientInstance: {},
    allInstances: [],
  }),
  created() {},
  mounted () {
    this.refreshClient();
    this.startExtensionsInterval()
  },
  computed: {
    ...mapGetters(['currentUser', 'isAuthenticated'])
  },
  methods: {
    refreshClient() {
      this.getClientInstance()
      this.getClientExperiments()
      this.getRemoteInstances()
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
    getClientExperiments() {
      kaapanaApiService
        .federatedClientApiGet("/experiments",{
        limit: 100,
        }).then((response) => {
          this.clientExperiments = response.data;
        })
        .catch((err) => {
          console.log(err);
        });
    },
    getRemoteInstances() {
      kaapanaApiService
        .federatedClientApiPost("/get-remote-kaapana-instances")
        .then((response) => {
          this.allInstances = response.data;
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
        // if (!this.$refs.workflowexecution.dialogOpen) {
        this.refreshClient();
        // }
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
