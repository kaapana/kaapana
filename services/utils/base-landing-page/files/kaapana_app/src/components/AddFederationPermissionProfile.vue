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
            v-model="selected_remote_instance_name"
            :items="remoteInstanceNames"
          ></v-select>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click.stop="submitFederationPermissionProfileForm" :disabled="federationPermProfilePost.kaapana_instance === ''">submit</v-btn>
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

  props: {
      federation: {
        type: Object,
        required: true
      },
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
          // remote_instance_name: '',
          kaapana_instance: {},
          federation_id: '',
        },
        selected_remote_instance_name: '',
        remoteInstances: [],
        remoteInstanceNames: [],
        
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
            this.remoteInstances = response.data
            this.remoteInstanceNames = this.remoteInstances.map(object => object.instance_name);
            console.log("this.remoteInstances: ", this.remoteInstances)
          })
          .catch((err) => {
            console.log(err);
          });
      },
    // Function to find an instance by instance_name
    findInstanceByName(name) {
      return instances.find(instance => instance.instance_name === name);
    },
    submitFederationPermissionProfileForm () {
      this.federationPermProfilePost.federation_id = this.federation.federation_id;
      this.federationPermProfilePost.kaapana_instance = this.remoteInstances.find(instance => instance.instance_name === this.selected_remote_instance_name)
      console.log("this.federationPermProfilePost.kaapana_instance: ", this.federationPermProfilePost.kaapana_instance)
      if (this.federationPermProfilePost.kaapana_instance) {
        kaapanaApiService
          .federatedClientApiPost("/federation-permission-profile", this.federationPermProfilePost)
          .then((response) => {
            this.federationPermProfileDialog = false
            this.$emit('refreshFederationFromAdding')
            this.resetForm()
          })
          .catch((err) => {
            console.log(err);
          });
      }
      else {
        this.$notify({
          type: "error",
          title: "Please a connected remote instance!",
        });
      }
    },
  }
}

</script>
