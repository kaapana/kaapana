<template>
  <v-dialog v-model="remoteDialog" max-width="600px">
    <template v-slot:activator="{ on, attrs }">
      <v-btn v-bind="attrs" v-on="on" color="primary" small rounded outlined>
        add remote
      </v-btn>
    </template>
    <v-card>
      <v-form v-model="remoteValid" ref="remoteForm" lazy-validation="lazy-validation">
        <v-card-title><span class="text-h5">Remote Instance</span></v-card-title>
        <v-card-text>
          <v-container>
            <v-row>
              <p>Enter instance attributes in corresponding fields</p>
            </v-row>
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
                <v-checkbox v-model="remotePost.ssl_check" label="Verify SSL" required=""></v-checkbox>
              </v-col>
            </v-row>
          <v-row>
            <v-col cols="16">
              <v-divider></v-divider>
            </v-col>
          </v-row>
            <v-row>
              <v-textarea 
                v-model="pasteRemote" 
                label="Or just paste remote instance definition as json string" 
                placeholder="{
                  'instance_name': '<instance_name>', 
                  'host': '<host>', 
                  'port': '<port>', 
                  'token': '<token>', 
                  'fernet_key': '<fernet_key>', 
                  'ssl_check': '<true/false>'
                }"
                rows="8"
                outlined
              ></v-textarea>
            </v-row>
          </v-container>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn class="mr-4" @click="submitRemoteForm">submit</v-btn>
          <v-btn @click="resetForm">clear</v-btn>
        </v-card-actions>
      </v-form>
    </v-card>
  </v-dialog>
</template>

<script>
import kaapanaApiService from "@/common/kaapanaApi.service";

export default {
  name: "AddRemoteInstance",
  
  data() {
    return this.initialState();
  },

  watch: {
    pasteRemote() {
      // read pasted json string and transfer values
      try {
        let jsonData = JSON.parse(this.pasteRemote)
        this.remotePost.instance_name = jsonData.hasOwnProperty("instance_name") ? jsonData["instance_name"] : this.remotePost.instance_name;
        this.remotePost.host = jsonData.hasOwnProperty("host") ? jsonData["host"] : this.remotePost.host;
        this.remotePost.port = jsonData.hasOwnProperty("port") ? jsonData["port"] : this.remotePost.port;
        this.remotePost.token = jsonData.hasOwnProperty("token") ? jsonData["token"] : this.remotePost.token;
        this.remotePost.fernet_key = jsonData.hasOwnProperty("fernet_key") ? jsonData["fernet_key"] : this.remotePost.fernet_key;
        this.remotePost.ssl_check = jsonData.hasOwnProperty("ssl_check") ? jsonData["ssl_check"] : this.remotePost.ssl_check;
      } catch (error) {
        this.$notify({
          type: "error",
          title: "Please enter the instance definition in the correct json format with all fields defined!",
        });
      }
      
    }
  },

  computed: {
    requiredRule() {
      return [(v) => !!v || "This field is required"];
    },
  },

  methods: {
    initialState () {
      return {
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
        },
        pasteRemote: '',
      }
    },
    resetForm () {
      let resetData = this.initialState();
      // resetData["remoteDialog"] = true;
      Object.assign(this.$data, resetData);
    },
    submitRemoteForm () {
      if (this.remotePost.token || this.remotePost.host || this.remotePost.instance_name) {
        kaapanaApiService
          .federatedClientApiPost("/remote-kaapana-instance", this.remotePost)
          .then((response) => {
            this.remoteDialog = false
            this.$emit('refreshRemoteFromAdding')
            this.resetForm()
          })
          .catch((err) => {
            console.log(err);
          });
      }
      else {
        this.$notify({
          type: "error",
          title: "Please enter the instance definition in the correct json format with all fields defined!",
        });
      }
    },
  }
}

</script>
