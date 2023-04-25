<template>
  <v-container text-left fluid>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <!-- v-col cols=2 align="left"> Remote Instances </v-col -->
            <p class="mx-4 my-2">Runner Instances</p>
            <add-remote-instance class="mx-4" @refreshRemoteFromAdding="getKaapanaInstances()"></add-remote-instance>
            <sync-remote-instances class="mx-4" @refreshRemoteFromSyncing="getKaapanaInstances()"></sync-remote-instances>
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
  import SyncRemoteInstances from "@/components/SyncRemoteInstances.vue";

  export default Vue.extend({
    components: {
      AddRemoteInstance,
      KaapanaInstance,
      SyncRemoteInstances
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
  