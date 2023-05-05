<template lang="pug">
  .federated-panel
    v-container(text-left fluid)
      workflow-table(:workflows="clientWorkflows" @refreshView="getClientWorkflows()")
</template>

<script>
import Vue from "vue";
import { mapGetters } from "vuex";
import kaapanaApiService from "@/common/kaapanaApi.service";

import WorkflowTable from "@/components/WorkflowTable.vue"

export default Vue.extend({
  components: {
    WorkflowTable,
  },
  data: () => ({
    polling: 0,
    clientWorkflows: []
  }),
  created() {},
  mounted () {
    this.startExtensionsInterval()
  },
  computed: {
    ...mapGetters(['currentUser', 'isAuthenticated'])
  },
  methods: {
    getClientWorkflows() {
      kaapanaApiService
        .federatedClientApiGet("/workflows",{
        limit: 100,
        }).then((response) => {
          this.clientWorkflows = response.data;
          this.$notify({
            title: "Sucessfully refreshed workflow list.",
            type: "success"
          })
        })
        .catch((err) => {
          this.$notify({
            title: "Error while refreshing workflow list.",
            type: "error"
          })
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
        this.getClientWorkflows();
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
