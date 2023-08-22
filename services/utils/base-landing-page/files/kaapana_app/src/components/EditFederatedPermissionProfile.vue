<template>
  <v-dialog v-model="federatedPermissionProfileDialog" max-width="600px">
    <template v-slot:activator="{ on, attrs }">
      <v-btn v-bind="attrs" v-on="on" color="secondary" small rounded outlined>
        edit
      </v-btn>
    </template>
    <!-- <template v-slot:activator="{ on, attrs }">
      <v-tooltip >
        <template v-slot:activator='{ on, attrs }'>
          <v-btn v-bind="attrs" v-on="on" small icon>
            <v-icon color="secondary" dark='' v-bind='attrs' v-on='on'>
              mdi-pencil
            </v-icon>
          </v-btn>
        </template>
        <span> Edit Federated Permission Profile for local instance </span>
      </v-tooltip>
    </template> -->
    <v-card>
      <v-form v-model="federatedPermissionProfileValid" lazy-validation="lazy-validation">
        <v-card-title><span class="text-h5">New Federation</span></v-card-title>
        <v-card-text>
          <v-container>
            <!-- Federation accept status -->
            <v-row>
              <v-checkbox
                v-model="federatedPermissionProfilePost.federation_acception"
                label="Accept federation"
                required=""
              ></v-checkbox>
            </v-row>
            <!-- Role -->
            <v-row>
              <v-select
                v-model="federatedPermissionProfilePost.role"
                label="Role in federation: server or node"
                :items="['server', 'node']"
              ></v-select>
            </v-row>
            <!-- Auto Update -->
            <v-row>
              <v-checkbox
                v-model="federatedPermissionProfilePost.automatic_update"
                label="Automatically sync with remote instances for executable workflows"
                required=""
              ></v-checkbox>
            </v-row>
            <!-- Auto Execution -->
            <v-row>
              <v-checkbox
                v-model="federatedPermissionProfilePost.automatic_workflow_execution"
                label="Automatically execute workflows from remote instances"
                required=""
              ></v-checkbox>
            </v-row>
            <!-- Allowed Workflows -->
            <v-row>
              <v-select
                v-model="federatedPermissionProfilePost.allowed_dags"
                label="Allowed workflows"
                :items="available_dags"
                multiple=""
              ></v-select>
            </v-row>
            <!-- Allowed Datasets -->
            <v-row>
              <v-select
                v-model="federatedPermissionProfilePost.allowed_datasets"
                label="Allowed datasets"
                :items="available_datasets"
                multiple=""
              ></v-select>
            </v-row>
          </v-container>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn 
            color="primary" 
            @click.stop="submitFederatedPermissionProfileForm" 
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
import {loadDatasets} from "@/common/api.service";

export default {
  name: "FederatedPermissionProfile",
  
  data: () => ({
    // return this.initialState();
    federatedPermissionProfileValid: false,
    federatedPermissionProfileDialog: false,
    federatedPermissionProfilePost: {
      federated_permission_profile_id: '',
      federation_acception: false,
      role: '',
      automatic_update: false,
      automatic_workflow_execution: false,
      allowed_dags: [],
      allowed_datasets: [],
    },
    available_dags: [],
    available_datasets: [],
  }),

  props: {
      federated_permission_profile: {
        type: Object,
        required: true
      },
    },

  mounted () {
    // get list of available dags and datasets of fed_perm_profile's instance
    this.getDags();
    this.getDatasets();
    this.initialState();
  },

  watch: {
  },

  computed: {
  },

  methods: {
    initialState () {
      console.log("EDIT this.federated_permission_profile: ", this.federated_permission_profile)
      this.federatedPermissionProfilePost.federated_permission_profile_id = this.federated_permission_profile.federated_permission_profile_id
      this.federatedPermissionProfilePost.federation_acception = this.federated_permission_profile.federation_acception
      this.federatedPermissionProfilePost.role = this.federated_permission_profile.role
      this.federatedPermissionProfilePost.automatic_update = this.federated_permission_profile.automatic_update
      this.federatedPermissionProfilePost.automatic_workflow_execution = this.federated_permission_profile.automatic_workflow_execution
      this.federatedPermissionProfilePost.allowed_dags = this.federated_permission_profile.allowed_dags
      this.federatedPermissionProfilePost.allowed_datasets = this.federated_permission_profile.allowed_datasets.map(object => object.name);
    },
    resetForm () {
      let resetData = this.initialState();
      // resetData["federatedPermissionProfileDialog"] = true;
      Object.assign(this.$data, resetData);
    },

    // API calls
    getDags() {
        kaapanaApiService
          .federatedClientApiPost("/get-dags", {
            instance_names: [this.federated_permission_profile.kaapana_instance.instance_name],
            kind_of_dags: "all"
          })
          .then((response) => {
            this.available_dags = response.data;
            console.log("this.available_dags: ", this.available_dags, "type: ", typeof this.available_dags)
          })
          .catch((err) => {
            console.log(err);
          });
      },
      getDatasets() {
        loadDatasets().then(_datasetNames => {
          this.available_datasets = _datasetNames;
          console.log("this.available_datasets: ", this.available_datasets, "type: ", typeof this.available_datasets)
        })
      },
    submitFederatedPermissionProfileForm () {
      // add federated_permission_profile_id to this.federatedPermissionProfilePost
      this.federatedPermissionProfilePost.federated_permission_profile_id = this.federated_permission_profile.federated_permission_profile_id
      console.log("this.federatedPermissionProfilePost: ", this.federatedPermissionProfilePost)
      kaapanaApiService
        .federatedClientApiPut("/federation-permission-profile", this.federatedPermissionProfilePost)
        .then((response) => {
          this.$emit('refreshFederationFromEditing')
          this.federatedPermissionProfileDialog = false
          this.resetForm()
        })
        .catch((err) => {
          console.log(err);
        });
    },
  }
}

</script>
