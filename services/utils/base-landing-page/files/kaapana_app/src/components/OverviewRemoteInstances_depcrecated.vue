<template>
  <v-card>
    <v-card-title>
      <!-- v-col cols=2 align="left"> Remote Instances </v-col -->
      <p class="mx-4 my-2">Executing Instances </p>
      <add-remote-instance class="mx-4" @refreshRemoteFromAdding="refreshRemote()"></add-remote-instance>
      <sync-remote-instances class="mx-4" @refreshRemoteFromSyncing="refreshRemote()"></sync-remote-instances>
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
              @refreshView="refreshRemote()" 
              @ei="editRemoteInstance"
            ></RemoteKaapanaInstance>
          </v-col>
        </v-row>
      </v-container>
    </v-card-text>
    <v-card-actions></v-card-actions>
  </v-card>
</template>

<script>

  import kaapanaApiService from "@/common/kaapanaApi.service";
  import {loadDatasetNames} from "@/common/api.service";

  import RemoteKaapanaInstance  from "@/components/RemoteKaapanaInstance.vue";
  import AddRemoteInstance from "@/components/AddRemoteInstance.vue";
  import SyncRemoteInstances from "@/components/SyncRemoteInstances.vue";

  export default {
    name: 'OverviewRemoteInstances',

    components: {
      RemoteKaapanaInstance,
      AddRemoteInstance,
      SyncRemoteInstances,
    },

    data: () => ({
      remoteInstances: {},
    }),

    mounted () {
      this.refreshRemote()
    },

    methods: {
      refreshRemote () {
        this.getRemoteInstances()
      },
      editRemoteInstance(instance) {
        this.remotePost = instance
        this.remoteDialog = true
        this.remoteUpdate = true
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
  }
</script>
