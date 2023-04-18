<template>
  <v-container text-left fluid>
    <h2> Federated Learning </h2>
    <LocalKaapanaInstance
      v-if="clientInstance"
      :instance="clientInstance"
      :remote="false"
      @refreshView="refreshClient()"
      @ei="editClientInstance"
    ></LocalKaapanaInstance>
    <OverviewRemoteInstances></OverviewRemoteInstances>
  </v-container>
</template>
  
  <script>
  import Vue from "vue";
  import { mapGetters } from "vuex";
  import kaapanaApiService from "@/common/kaapanaApi.service";
  
  import LocalKaapanaInstance  from "@/components/LocalKaapanaInstance.vue";
  import OverviewRemoteInstances from "@/components/OverviewRemoteInstances.vue";
  
  export default Vue.extend({
    components: {
      LocalKaapanaInstance,
      OverviewRemoteInstances,
    },
    data: () => ({
      clientInstance: {},
    }),
    created() {
    },
    mounted () {
      console.log("Hello, I am the Federated Learning View!")
      this.refreshClient();
    },
    watch: {
    },
    computed: {
    },
    methods: {
      // General Methods
      refreshClient() {
        this.getClientInstance()
      },

      // Methods for Client Instance
      editClientInstance(instance) {
        this.clientPost = instance
        this.clientPost.fernet_encrypted = false
        this.clientDialog = true
        this.clientUpdate = true
      },

      // API Calls
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
    },
  });
  </script>
  
  <style lang="scss">
  
  </style>
  