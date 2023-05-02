<template>
  <v-dialog v-model="remoteDialog" max-width="600px">
    <template v-slot:activator="{ on, attrs }">
      <v-btn v-bind="attrs" v-on="on" color="primary" small rounded outlined>
        <!-- v-icon color="primary" >mdi-plus-circle</v-icon -->
        add remote
      </v-btn>
      <!-- v-btn v-bind="attrs" v-on="on" small icon>
        <v-icon color="primary" dark >mdi-plus-circle</v-icon>
      </v-btn -->
    </template>
    <v-card>
      <v-form v-model="remoteValid" ref="remoteForm" lazy-validation="lazy-validation">
        <v-card-title><span class="text-h5">Remote Instance</span></v-card-title>
        <v-card-text>
          <v-container>
            <v-row>
              <v-col cols="5">
                <v-text-field v-model="remotePost.instance_name" label="Instance name" required="" :disabled="remoteUpdate"></v-text-field>
              </v-col>
              <v-col cols="5">
                <v-text-field v-model="remotePost.host" label="Host" required="" :disabled="remoteUpdate"></v-text-field>
              </v-col>
              <v-col cols="2">
                <v-text-field v-model="remotePost.port" label="Port" type="number" required=""></v-text-field>
              </v-col>
              <v-col cols="5">
                <v-text-field v-model="remotePost.token" label="Token" required=""></v-text-field>
              </v-col>
              <v-col cols="5">
                <v-text-field v-model="remotePost.fernet_key" label="Fernet Key" required=""></v-text-field>
              </v-col>
              <v-col cols="2">
                <v-checkbox v-model="remotePost.ssl_check" label="SSL" required=""></v-checkbox>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn class="mr-4" @click="submitRemoteForm">submit</v-btn>
          <v-btn @click="resetRemoteForm">clear</v-btn>
        </v-card-actions>
      </v-form>
    </v-card>
  </v-dialog>
</template>

<script>
import kaapanaApiService from "@/common/kaapanaApi.service";

export default {
  name: "AddRemoteInstance",
  
  data: () => ({
    remoteValid: false,
    remoteUpdate: false,
    remoteDialog: false,
    remoteJobs: [],
    remotePost: {
      ssl_check: false,
      token: '',
      host: '',
      instance_name: '',
      port: 443,
      fernet_key: 'deactivated',
    }
  }),

  methods: {
    resetRemoteForm () {
      this.$refs.remoteForm.reset()
    },
    submitRemoteForm () {
      kaapanaApiService
        .federatedClientApiPost("/remote-kaapana-instance", this.remotePost)
        .then((response) => {
          this.remoteDialog = false
          this.$emit('refreshRemoteFromAdding')
          this.resetRemoteForm()
        })
        .catch((err) => {
          console.log(err);
        });
    }
  }
}

</script>