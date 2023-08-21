
<template>
  <v-card fluid="">
    <v-card-title>
      <v-col>
        <v-tooltip v-if="!federation.remote" bottom=''>
          <template v-slot:activator='{ on, attrs }'>
            <v-icon color="primary" dark='' v-bind='attrs' v-on='on'>
              | mdi-home
            </v-icon>
          </template>
          <span> locally managed federation </span>
        </v-tooltip>
        <v-tooltip v-if="federation.remote" bottom=''>
          <template v-slot:activator='{ on, attrs }'>
            <v-icon color="primary" dark='' v-bind='attrs' v-on='on'>
              | mdi-cloud-braces
            </v-icon>
          </template>
          <span> remotely managed federation </span>
        </v-tooltip>
      </v-col>
      <v-col cols="3">
        <p>Federation name: {{ federation.federation_name }}</p>
      </v-col>
      <v-col cols="3">
        <p>Federation ID: {{ federation.federation_id }}</p>
      </v-col>
      <v-col >
        <AddFederationPermissionProfile class="mx-4"></AddFederationPermissionProfile>
      </v-col>
      <v-col >
        <v-tooltip v-if="!federation.remote" bottom=''>
          <template v-slot:activator='{ on, attrs }'>
            <v-btn v-bind="attrs" v-on="on" @click='deleteFederation()' small icon>
              <v-icon color="red" dark='' v-bind='attrs' v-on='on'>
                mdi-trash-can-outline
              </v-icon>
            </v-btn>
          </template>
          <span> delete federation </span>
        </v-tooltip>
      </v-col>
    </v-card-title>
    <v-card-text class=text-primary>
      <!-- <v-row>
        <p> Federation's instances</p>
      </v-row> -->
      <v-row>
        <v-data-table
          :headers="federatedPermissionProfilesHeaders"
          :items="all_fed_perm_profiles"
          item-key="kaapana_instance.instance_name"
          class="elevation-1"
        >
          <!-- local or remote indicator -->
          <template v-slot:item.remote="{ item }">
            <v-tooltip v-if="item.federated_permission_profile_id === federation.owner_federated_permission_profile.federated_permission_profile_id" bottom=''>
              <template v-slot:activator='{ on, attrs }'>
                <v-icon color="secondary" dark='' v-bind='attrs' v-on='on'>
                  | mdi-home
                </v-icon>
              </template>
              <span> Federated Permission Profile for local instance </span>
            </v-tooltip>
            <v-tooltip v-if="!item.federated_permission_profile_id === federation.owner_federated_permission_profile.federated_permission_profile_id" bottom=''>
              <template v-slot:activator='{ on, attrs }'>
                <v-icon color="primary" dark='' v-bind='attrs' v-on='on'>
                  | mdi-cloud-braces
                </v-icon>
              </template>
              <span> Federated Permission Profile for remote instance </span>
            </v-tooltip>
          </template>
          <!-- Federation acctepted status -->
          <template v-slot:item.federation_acception="{ item }">
            <v-icon v-if="item.federation_acception" color="green">
              mdi-check-circle-outline
            </v-icon>
            <v-icon v-if="!item.federation_acception" color="red">
              mdi-close-circle-outline
            </v-icon>
          </template>
          <!-- Auto Updates -->
          <template v-slot:item.automatic_update="{ item }">
            <v-icon v-if="item.automatic_update" color="green">
              mdi-check-circle-outline
            </v-icon>
            <v-icon v-if="!item.automatic_update" color="red">
              mdi-close-circle-outline
            </v-icon>
          </template>
          <!-- Auto Execution -->
          <template v-slot:item.automatic_workflow_execution="{ item }">
            <v-icon v-if="item.automatic_workflow_execution" color="green">
              mdi-check-circle-outline
            </v-icon>
            <v-icon v-if="!item.automatic_workflow_execution" color="red">
              mdi-close-circle-outline
            </v-icon>
          </template>
          <!-- Allowed Dags -->
          <template v-slot:item.allowed_dags="{ item }">
            <v-chip v-for='dag in item.allowed_dags' small> {{ dag }} </v-chip>
          </template>
          <!-- Allowed Dags -->
          <template v-slot:item.allowed_datasets="{ item }">
            <v-chip v-for='dataset in item.allowed_datasets' small> {{ dataset.name }} </v-chip>
          </template>
          <!-- Actions -->
          <template v-slot:item.actions="{ item }">
            <!-- local -> edit permissions as action -->
            <template v-if="item.federated_permission_profile_id === federation.owner_federated_permission_profile.federated_permission_profile_id" bottom=''>
              <EditFederatedPermissionProfile
                :federated_permission_profile = "item"
                @refreshFederationFromEditing="callEmitRefreshFederationFromFederation()"
                class="mx-4"
              ></EditFederatedPermissionProfile>
            </template>
            <!-- remote -> delete permission profile as action -->
            <v-tooltip v-if="!item.federated_permission_profile_id === federation.owner_federated_permission_profile.federated_permission_profile_id" bottom=''>
              <template v-slot:activator='{ on, attrs }'>
                <v-btn v-bind="attrs" v-on="on" @click='deleteFederationPermissionProfile(item)' small icon>
                  <v-icon color="secondary" dark='' v-bind='attrs' v-on='on'>
                    mdi-trash-can-outline
                  </v-icon>
                </v-btn>
              </template>
              <span> Delete Federated Permission Profile for remote instance </span>
            </v-tooltip>
          </template>
        </v-data-table>
      </v-row>
    </v-card-text>
  </v-card>
</template>
  
  <script>
  
  import kaapanaApiService from "@/common/kaapanaApi.service";
  
  // import FederatedPermissionProfile from "@/components/FederatedPermissionProfile.vue";
  import AddFederationPermissionProfile from "@/components/AddFederationPermissionProfile.vue";
  import EditFederatedPermissionProfile from "@/components/EditFederatedPermissionProfile.vue";
  
  export default {
    components: {
      // FederatedPermissionProfile,
      AddFederationPermissionProfile,
      EditFederatedPermissionProfile,
    },

    name: 'Federation',

    data: () => ({
      federatedPermissionProfilesHeaders: [
        { text: '', value: 'remote' },
        { text: 'Instance Name', align: 'start', value: 'kaapana_instance.instance_name' },
        { text: 'Instance ID', value: 'kaapana_instance.id' },
        { text: 'Permissions ID', value: 'federated_permission_profile_id' },
        { text: 'Federation accepted', value: 'federation_acception', align: 'center' },
        { text: 'Role', value: 'role' },
        { text: 'Auto Updates', value: 'automatic_update', align: 'center' },
        { text: 'Auto Execution', value: 'automatic_workflow_execution', align: 'center'},
        { text: 'Allowed Workflows', value: 'allowed_dags' },
        { text: 'Allowed Datasets', value: 'allowed_datasets' },
        { text: 'Actions', value: 'actions', sortable: false, filterable: false, align: 'center'},
      ],
      all_fed_perm_profiles: [],
    }),

    props: {
      federation: {
        type: Object,
        required: true
      },
    },

    mounted () {
      this.printFed()
      this.retrieveAllFedPermProfiles()
    },

    watch: {
    },

    computed: {
    },

    methods:{
      printFed() {
        console.log("federation: ", this.federation)
      },
      retrieveAllFedPermProfiles() {
        // compute set from owner and participating fed_perm_profiles of federation
        this.all_fed_perm_profiles = [...new Map([...this.federation.participating_federated_permission_profiles, this.federation.owner_federated_permission_profile].map(obj => [obj.id, obj])).values()];
        console.log("this.all_fed_perm_profiles: ", this.all_fed_perm_profiles)
      },
      callEmitRefreshFederationFromFederation() {
        // refresh list of Federations
        this.$emit('refreshFederationFromFederation')
      },

      // API Calls
      deleteFederation() {
        const federation_id = this.federation.federation_id
        kaapanaApiService
          .federatedClientApiDelete("/federation",{
            federation_id,
          }).then((response) => {
            // call emit to refresh federations in parent component
            // positive notification
            const message = `Successfully deleted federation ${federation_id}`
            this.$notify({
              type: 'success',
              title: message,
            })
          })
          .catch((err) => {
            this.loading = false
            // negative notification
            const message = `Error while deleting federation ${federation_id}`
            this.$notify({
              type: "error",
              title: message,
            })
            console.log(err);
          })
          this.callEmitRefreshFederationFromFederation()
      },
    }
  }
  </script>
  
  <!-- Add "scoped" attribute to limit CSS to this component only -->
  <style scoped lang="scss">
  
  
  </style>
  