<template>
  <v-dialog v-model=viewremoteList max-width="900px">
    <template v-slot:activator="{ on, attrs }">
      <v-btn v-bind="attrs" v-on="on" small icon>
        <v-icon color="primary" dark x-large>mdi-eye</v-icon>
      </v-btn>
    </template>
    <v-card>
      <v-card-title><span class="text-h5">Remote Instances</span></v-card-title>
      <v-card-text>
        <v-container fluid="">
          <v-row dense="">
            <v-col v-for="instance in remoteInstances" :key="instance.id" cols="6" align="left">
              <!-- former old KaapanaInstance-->
              <RemoteKaapanaInstance :instance="instance" :remote="instance.remote" @refreshView="refreshRemote()" @ei="editRemoteInstance"></RemoteKaapanaInstance>
            </v-col>
          </v-row>
        </v-container>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <add-remote-instance ref="addremoteinstance" :remote='true'></add-remote-instance>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
  
  <script>
  import kaapanaApiService from "@/common/kaapanaApi.service";
  
  import RemoteKaapanaInstance  from "@/components/RemoteKaapanaInstance.vue";
  import AddRemoteInstance from "@/components/AddRemoteInstance.vue";
    
  export default {
    name: "ViewRemoteInstances",

    components: {
      RemoteKaapanaInstance,
      AddRemoteInstance
    },
    
    data: () => ({
      viewremoteList: false,
      clientInstance: {},
      remoteInstances: {},
    }),
  
    props: {
      remote: {
        type: Boolean,
        required: true,
      },
      clientinstance: {
        type: Object,
        required: true
      }
    },

    mounted () {
      this.refreshRemote();
    },

    watch: {
      viewremoteList (visible) {
        if (visible) {
          this.refreshRemote();
        }
      }
    },
  
    methods: {
      refreshRemote () {
        this.getRemoteInstances()
        this.getRemoteJobs()
      },
      editRemoteInstance(instance) {
        this.remotePost = instance
        this.remoteDialog = true
        this.remoteUpdate = true
      },
      deleteRemoteInstances() {
        kaapanaApiService
          .federatedClientApiDelete("/remote-kaapana-instances")
          .then((response) => {

          })
          .catch((err) => {
            console.log(err);
          });
      },
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
      getRemoteJobs() {
        kaapanaApiService
          .federatedRemoteApiGet("/jobs", {
          limit: 100,
          }).then((response) => {
            this.remoteJobs = response.data;
          })
          .catch((err) => {
            console.log(err);
          });
      },
    }
  }
  
  </script>