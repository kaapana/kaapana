<template>
  <v-dialog v-model="federationPermProfileDialog" max-width="600px">
    <template v-slot:activator="{ on, attrs }">
      <v-btn v-bind="attrs" v-on="on" color="primary" small rounded outlined>
        add instance
      </v-btn>
    </template>
    <v-card>
      <v-form v-model="federationPermProfileValid" lazy-validation="lazy-validation">
        <v-card-title><span class="text-h5">Add new instance to federation</span></v-card-title>
        <v-card-text>
          <v-select
            v-model="federationPermProfilePost.remote_instance"
            :items="remoteInstances"
          ></v-select>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click.stop="submitFederationPermissionProfileForm" :disabled="federationPermProfilePost.remote_instance === ''">submit</v-btn>
          <v-btn @click="resetForm">clear</v-btn>
        </v-card-actions>
      </v-form>
    </v-card>
  </v-dialog>
</template>

<script>
import kaapanaApiService from "@/common/kaapanaApi.service";

export default {
  name: "AddFederationPermissionProfile",
  
  data() {
    return this.initialState();
  },

  mounted () {
    // get all remote Kaapana instances
    this.getKaapanaInstances()
  },

  watch: {
  },

  computed: {
  },

  methods: {
    initialState () {
      console.log("Initializing state...");
      return {
        federationPermProfileValid: false,
        federationPermProfileDialog: false,
        federationPermProfilePost: {
          remote_instance: '',
        },
        remoteInstances: [],
      }
    },
    resetForm () {
      let resetData = this.initialState();
      // resetData["federationPermProfileDialog"] = true;
      Object.assign(this.$data, resetData);
    },
    getKaapanaInstances() {
        kaapanaApiService
          .federatedClientApiPost("/get-kaapana-instances")
          .then((response) => {
            this.remoteInstances = response.data;
            console.log("this.remoteInstances: ", this.remoteInstances)
          })
          .catch((err) => {
            console.log(err);
          });
      },
    submitFederationPermissionProfileForm () {
      console.log("this.federationPermProfilePost.federation_name: ", this.federationPermProfilePost.federation_name)
      if (this.federationPermProfilePost.federation_name) {
        kaapanaApiService
          .federatedClientApiPost("/federation", this.federationPermProfilePost)
          .then((response) => {
            this.federationPermProfileDialog = false
            this.$emit('refreshFederationFromCreating')
            this.resetForm()
          })
          .catch((err) => {
            console.log(err);
          });
      }
      else {
        this.$notify({
          type: "error",
          title: "Please enter a federation name!",
        });
      }
    },
  }
}

</script>
