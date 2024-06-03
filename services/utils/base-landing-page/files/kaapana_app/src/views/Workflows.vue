<template>
  <div class="federated-panel">
    <IdleTracker />
    <v-container text-left="text-left" fluid="fluid">
      <workflow-table
        :workflows="clientWorkflows"
        :extLoading="workflowTableLoading"
        @refreshView="getClientWorkflows()"
        @update:itemsPerPage="updateItemsPerPage" 
        @update:page="updateCurrentPage"
      ></workflow-table>
    </v-container>
  </div>
</template>

<script>
import Vue from "vue";
import { mapGetters } from "vuex";
// import kaapanaApiService from "@/common/kaapanaApi.service";

import WorkflowTable from "@/components/WorkflowTable.vue";
import IdleTracker from "@/components/IdleTracker.vue";
export default {
  components: {
    WorkflowTable,
    IdleTracker,
  },
  data: () => ({
    polling: 0,
    clientWorkflows: [],
    workflowTableLoading: false,
  }),
  created() {},
  mounted() {
    this.workflowTableLoading = true;
    this.startExtensionsInterval();
  },
  computed: {
    ...mapGetters(["currentUser", "isAuthenticated"]),
  },
  methods: {
    getClientWorkflows() {
      this.workflowTableLoading = true;
      kaapanaApiService
        .federatedClientApiGet("/workflows", {
          limit: this.itemsPerPage,
          offset: this.currentPage * this.itemsPerPage,
        })
        .then((response) => {
          this.workflowTableLoading = false;
          this.clientWorkflows = response.data;
          this.$notify({
            title: "Sucessfully refreshed workflow list.",
            type: "success",
          });
        })
        .catch((err) => {
          this.workflowTableLoading = false;
          this.$notify({
            title: "Error while refreshing workflow list.",
            type: "error",
          });
          console.log(err);
        });
    },
    updateItemsPerPage(newItemsPerPage) {
      this.itemsPerPage = newItemsPerPage;
      this.currentPage = 1; // Reset to the first page when itemsPerPage changes
      this.getClientWorkflows();
    },

    updateCurrentPage(newPage) {
      this.currentPage = newPage;
      this.getClientWorkflows(); // Re-fetch workflows with the new page
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
    },
  },
  beforeDestroy() {
    this.clearExtensionsInterval();
  },
};
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
  margin-bottom: 20px;
  /* add horizontal space between items */
}
</style>
