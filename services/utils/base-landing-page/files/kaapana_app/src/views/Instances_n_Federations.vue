<template>
  <v-container text-left fluid>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <p class="mx-4 my-2">Instances</p>
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
    <v-row>
      <v-col>
        <v-card>
          <v-card-title>
            <p class="mx-4 my-2">Federations</p>
            <create-federation class="mx-4" @refreshFederationFromCreating="getFederations()"></create-federation>
          </v-card-title>
          <v-card-text>
            <v-container fluid="">
              <v-row  
                v-for="federation in federations" 
                :key="federation.federation_id"
              >
                <v-col cols="12">
                  <Federation
                    :federation="federation"
                  ></Federation>
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
  import CreateFederation from "@/components/CreateFederation.vue";
  import Federation from "@/components/Federation.vue";

  export default Vue.extend({
    components: {
      AddRemoteInstance,
      CreateFederation,
      KaapanaInstance,
      Federation,
    },
    data: () => ({
      polling: 0,
      remoteInstances: {},
      federations: {},
    }),

    mounted () {
      this.getKaapanaInstances();
      this.getFederations();
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
          this.getKaapanaInstances()
        })
      },
      getFederations() {
        kaapanaApiService
          .federatedClientApiGet("/federations")
          .then((response) => {
            this.federations = response.data;
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
  