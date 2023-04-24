<template lang="pug">
  .federated-panel
    v-container(text-left fluid)
      experiment-table(:experiments="clientExperiments" @refreshView="getClientExperiments()")
</template>

<script>
import Vue from "vue";
import { mapGetters } from "vuex";
import kaapanaApiService from "@/common/kaapanaApi.service";

import ExperimentTable from "@/components/ExperimentTable.vue"

export default Vue.extend({
  components: {
    ExperimentTable,
  },
  data: () => ({
    polling: 0,
    clientExperiments: []
  }),
  created() {},
  mounted () {
    this.getClientExperiments();
    this.startExtensionsInterval()
  },
  computed: {
    ...mapGetters(['currentUser', 'isAuthenticated'])
  },
  methods: {
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
    clearExtensionsInterval() {
      window.clearInterval(this.polling);
    },
    startExtensionsInterval() {
      this.polling = window.setInterval(() => {
        // a little bit ugly... https://stackoverflow.com/questions/40410332/vuejs-access-child-components-data-from-parent
        // if (!this.$refs.workflowexecution.dialogOpen) {
        this.getClientExperiments();
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
