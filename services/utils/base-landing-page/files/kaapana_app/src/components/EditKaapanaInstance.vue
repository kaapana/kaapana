<template>
  <v-dialog v-model="kaapanaInstanceDialog" max-width="600px">
    <template v-slot:activator="{ on, attrs }">
      <v-btn v-bind="attrs" v-on="on" color="primary" small icon>
        <v-icon color="primary" dark='' v-bind='attrs' v-on='on'>
          mdi-pencil
        </v-icon>
      </v-btn>
    </template>
    <v-card>
      <v-form v-model="kaapanaInstanceValid" lazy-validation="lazy-validation">
        <v-card-title>
          <span class="text-h5">Edit Kaapana Instance</span>
        </v-card-title>
        <v-card-text>
          <v-container>
            <!-- Network w/ Port -->
            <v-row v-if="editedKaapanaInstance.remote">
              <v-text-field
                v-model="editedKaapanaInstance.port"
                label="HTTP Port"
                required=""
              ></v-text-field>
            </v-row>
            <!-- Token -->
            <v-row v-if="editedKaapanaInstance.remote">
              <v-text-field
                v-model="editedKaapanaInstance.token"
                label="Token"
                required=""
              ></v-text-field>
            </v-row>
            <!-- SSL -->
            <v-row>
              <v-checkbox
                v-model="editedKaapanaInstance.ssl_check"
                label="Verify SSL"
                required=""
              ></v-checkbox>
            </v-row>
            <!-- Fernet encryption -->
            <v-row>
              <v-checkbox
                v-if="!editedKaapanaInstance.remote"
                v-model="editedKaapanaInstance.fernet_encrypted"
                label="Fernet Encryption"
                required=""
              ></v-checkbox>
              <v-text-field
                v-if="editedKaapanaInstance.remote"
                v-model="editedKaapanaInstance.fernet_key"
                label="Token"
                required=""
              ></v-text-field>
            </v-row>
          </v-container>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn 
            color="primary" 
            @click.stop="submitKaapanaInstanceForm"
          >
            submit
          </v-btn>
          <v-btn @click="resetForm">clear</v-btn>
        </v-card-actions>
      </v-form>
    </v-card>
  </v-dialog>
</template>

<script>
import kaapanaApiService from "@/common/kaapanaApi.service";

export default {
  name: "EditKaapanaInstance",
  
  data: () => ({
    kaapanaInstanceValid: false,
    kaapanaInstanceDialog: false,
    editedKaapanaInstance: {},
  }),

  props: {
      kaapana_instance: {
        type: Object,
        required: true
      },
    },

  mounted () {
  },

  watch: {
    kaapanaInstanceDialog() {
      this.initialState();
    }
  },

  computed: {
  },

  methods: {
    initialState () {
      console.log("EDIT this.kaapana_instance: ", this.kaapana_instance)
      if (this.kaapana_instance.fernet_key != "deactivated") {
        this.kaapana_instance.fernet_encrypted = true
      } else {
        this.kaapana_instance.fernet_encrypted = false
      }
      this.editedKaapanaInstance = this.kaapana_instance
      console.log("EDIT this.editedKaapanaInstance: ", this.editedKaapanaInstance)
    },
    resetForm () {
      let resetData = this.initialState();
      resetData["kaapanaInstanceDialog"] = true;
      Object.assign(this.$data, resetData);
    },

    // API calls
    submitKaapanaInstanceForm () {
      console.log("SUBMIT this.editedKaapanaInstance: ", this.editedKaapanaInstance)
      let target_endpoint = ""
      let payload = ""
      if (this.kaapana_instance.remote) {
        target_endpoint = "/remote-kaapana-instance";
        payload = {
          "instance_name": this.editedKaapanaInstance["instance_name"],
          "host": this.editedKaapanaInstance["host"],
          "port": this.editedKaapanaInstance["port"],
          "token": this.editedKaapanaInstance["token"],
          "ssl_check": this.editedKaapanaInstance["ssl_check"],
          "fernet_key": this.editedKaapanaInstance["fernet_key"],
        }
      }
      else {
        target_endpoint = "/client-kaapana-instance";
        payload = {
          "ssl_check": this.editedKaapanaInstance["ssl_check"],
          "fernet_encrypted": this.editedKaapanaInstance["fernet_encrypted"],
        }
      }
      console.log("SUBMIT payload: ", payload)
      console.log("SUBMIT target_endpoint: ", target_endpoint)
      kaapanaApiService
        .federatedClientApiPut(target_endpoint, payload)
        .then((response) => {
          this.$emit('refreshInstancesFromEditing')
          this.kaapanaInstanceDialog = false
          this.resetForm()
        })
        .catch((err) => {
          console.log(err);
        });
    },
  }
}

</script>
