<template>
  <v-dialog v-model="viewremoteList" max-width="900px">
    <template v-slot:activator="{ on, attrs }">
      <v-btn color="primary" v-bind="attrs" v-on="on" dark="dark">View Remote Instances</v-btn>
    </template>
    <v-card>
        <v-card-title><span class="text-h5">Remote Instances</span></v-card-title>
        <v-card-text>
          <v-container fluid="">
            <v-row dense="">
              <v-col v-for="instance in remoteInstances" :key="instance.id" cols="6" align="left">
                <KaapanaInstance :instance="instance" :remote="instance.remote" @refreshView="refreshRemote()" @ei="editRemoteInstance"></KaapanaInstance>
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
  
  import KaapanaInstance  from "@/components/KaapanaInstance.vue";
  import AddRemoteInstance from "@/components/AddRemoteInstance.vue";
    
  export default {
    name: "ViewRemoteInstances",

    components: {
      KaapanaInstance,
      AddRemoteInstance
    },
    
    data: () => ({
      viewremoteList: false,
      clientInstance: {},
      remoteInstances: {},
    }),
  
    mounted () {
      this.refreshRemote();
    },
  
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