<template>
  <div class="federated-panel">
    <IdleTracker />
    <v-container text-left="text-left" fluid="fluid">
      <workflow-table
        :workflows="clientWorkflows"
        :extLoading="workflowTableLoading"
        :total-items="totalItems"
        :options.sync="options"
        @refreshView="getClientWorkflows"
        @update:options="getClientWorkflows"
      ></workflow-table>
    </v-container>
  </div>
</template>

<script>
import Vue from "vue";
import { mapGetters } from "vuex";
import kaapanaApiService from "@/common/kaapanaApi.service";

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
    totalItems: 0,
    search_string: "",
    options: {
      page: 1,
      itemsPerPage: 5,
      search: "",
    },
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
      console.log("Fetching workflows");
      this.workflowTableLoading = true;
      const { page, itemsPerPage, search } = this.options;
      console.log("Search: ", search);
      kaapanaApiService
        .federatedClientApiGet("/workflows", {
          limit: itemsPerPage,
          offset: (page - 1) * itemsPerPage,
          search: search,
        })
        .then((response) => {
          this.workflowTableLoading = false;
          this.clientWorkflows = response.data[0];
          this.totalItems = response.data[1];
          if (search === "") {
            this.$notify({
              title: "Sucessfully refreshed workflow list.",
              type: "success",
            });
          }
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

    clearExtensionsInterval() {
      window.clearInterval(this.polling);
    },
    // TODO Workflow list auto-refresh variable exported into settings/config.
    startExtensionsInterval() {
      console.log("Surprise refresh");
      this.polling = window.setInterval(() => {
        this.getClientWorkflows();
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
