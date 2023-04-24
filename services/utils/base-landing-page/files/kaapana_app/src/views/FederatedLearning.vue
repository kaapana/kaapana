<template>
  <v-container text-left fluid>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <!-- v-col cols=2 align="left"> Remote Instances </v-col -->
            <p class="mx-4 my-2">Runner Instances</p>
            <add-remote-instance class="mx-4" @refreshRemoteFromAdding="getRemoteInstances()"></add-remote-instance>
            <sync-remote-instances class="mx-4" @refreshRemoteFromSyncing="getRemoteInstances()"></sync-remote-instances>
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
                  <RemoteKaapanaInstance 
                    :instance="instance"
                    @refreshView="getRemoteInstances()" 
                  ></RemoteKaapanaInstance>
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
  import { mapGetters } from "vuex";
  import kaapanaApiService from "@/common/kaapanaApi.service";

  import AddRemoteInstance from "@/components/AddRemoteInstance.vue";
  import RemoteKaapanaInstance  from "@/components/RemoteKaapanaInstance.vue";
  import SyncRemoteInstances from "@/components/SyncRemoteInstances.vue";

  export default Vue.extend({
    components: {
      AddRemoteInstance,
      RemoteKaapanaInstance,
      SyncRemoteInstances
    },
    data: () => ({
      remoteInstances: {},
    }),

    mounted () {
      this.getRemoteInstances()
    },

    methods: {
      refreshRemote () {
        this.getRemoteInstances()
      },
      // API calls
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
      // TODO: API call to fill editRemoteInstance() with life
      // putRemoteInstance() {
      // }
    }
  });
</script>
  <style lang="scss">
  
  </style>
  