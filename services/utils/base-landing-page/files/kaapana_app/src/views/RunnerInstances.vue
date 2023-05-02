<template>
  <v-container text-left fluid>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <p class="mx-4 my-2">Instance Overview</p>
            <add-remote-instance class="mx-4" @refreshRemoteFromAdding="getKaapanaInstances()"></add-remote-instance>
            <v-btn class="mx-4" @click="checkForRemoteUpdates" color="primary" small outlined rounded>
              sync remotes
            </v-btn>
          </v-card-title>
          <v-card-text>
            <v-container fluid="">
              <v-row dense="">
                <v-col 
                  v-for="instance in remoteInstances" 
                  :key="instance.id"
                  cols="6"
                  align="left"
                >
                  <!-- former old KaapanaInstance-->
                  <KaapanaInstance 
                    :instance="instance"
                    @refreshView="getKaapanaInstances()" 
                  ></KaapanaInstance>
                </v-col>
              </v-row>
            </v-container>
          </v-card-text>
          <v-card-actions></v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>
  
  <script>
  import Vue from "vue";
  import kaapanaApiService from "@/common/kaapanaApi.service";

  import AddRemoteInstance from "@/components/AddRemoteInstance.vue";
  import KaapanaInstance  from "@/components/KaapanaInstance.vue";

  export default Vue.extend({
    components: {
      AddRemoteInstance,
      KaapanaInstance,
    },
    data: () => ({
      polling: 0,
      remoteInstances: {},
    }),

    mounted () {
      this.getKaapanaInstances();
      this.startExtensionsInterval()
    },

    methods: {
      // API calls
      getKaapanaInstances() {
        kaapanaApiService
          .federatedClientApiPost("/get-kaapana-instances")
          .then((response) => {
            this.remoteInstances = response.data;
          })
          .catch((err) => {
            console.log(err);
          });
      },
      checkForRemoteUpdates() {
        kaapanaApiService.syncRemoteInstances().then(successful => {
          console.log(successful)
          this.getKaapanaInstances()
        })
      },
      clearExtensionsInterval() {
        window.clearInterval(this.polling);
      },
      startExtensionsInterval() {
        this.polling = window.setInterval(() => {
          // a little bit ugly... https://stackoverflow.com/questions/40410332/vuejs-access-child-components-data-from-parent
          // if (!this.$refs.workflowexecution.dialogOpen) {
          this.getKaapanaInstances();
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
  
  </style>
  