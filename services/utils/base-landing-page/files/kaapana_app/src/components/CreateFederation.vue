<template>
  <v-dialog v-model="federationDialog" max-width="600px">
    <template v-slot:activator="{ on, attrs }">
      <v-btn v-bind="attrs" v-on="on" color="primary" small rounded outlined>
        create
      </v-btn>
    </template>
    <v-card>
      <v-form v-model="federationValid" lazy-validation="lazy-validation">
        <v-card-title><span class="text-h5">New Federation</span></v-card-title>
        <v-card-text>
          <v-container>
            <v-row>
              <v-col>
                <v-text-field v-model="federationPost.federation_name" label="Federation name" required=""></v-text-field>
              </v-col>
              <!-- select registered remote instances --> 
            </v-row>
          </v-container>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click.stop="submitFederationForm" :disabled="federationPost.federation_name === ''">submit</v-btn>
          <v-btn @click="resetForm">clear</v-btn>
        </v-card-actions>
      </v-form>
    </v-card>
  </v-dialog>
</template>

<script>
import kaapanaApiService from "@/common/kaapanaApi.service";

export default {
  name: "CreateFederation",
  
  data() {
    return this.initialState();
  },

  watch: {
  },

  computed: {
  },

  methods: {
    initialState () {
      console.log("Initializing state...");
      return {
        federationValid: false,
        federationDialog: false,
        federationPost: {
          federation_name: '',
          remote: false,
        },
      }
    },
    resetForm () {
      let resetData = this.initialState();
      // resetData["federationDialog"] = true;
      Object.assign(this.$data, resetData);
    },
    submitFederationForm () {
      console.log("this.federationPost.federation_name: ", this.federationPost.federation_name)
      if (this.federationPost.federation_name) {
        kaapanaApiService
          .federatedClientApiPost("/federation", this.federationPost)
          .then((response) => {
            this.federationDialog = false
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
