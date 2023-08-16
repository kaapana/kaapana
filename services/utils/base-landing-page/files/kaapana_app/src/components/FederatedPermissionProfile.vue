
<template>
  <v-card fluid>
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
      <v-col>
        <p>Federation name: {{ federation.federation_name }}</p>
      </v-col>
      <v-col>
        <p>Federation ID: {{ federation.federation_id }}</p>
      </v-col>
    </v-card-title>
    <v-card-text class=text-primary>
      <v-row>
        <p> Owner Federated Permission Profile:</p>
      </v-row>
      <v-row>
        <FederatedPermissionProfile
          :fed_perm_profile="federation.owner_federated_permission_profile"
        ></FederatedPermissionProfile>
      </v-row>
      <!-- <v-row>
        <v-col>
          <p> Owner ID: {{ federation.owner_federated_permission_profile.federated_permission_profile_id }}</p>
        </v-col>
        <v-col>
          <p> Kaapana Instance: {{ federation.owner_federated_permission_profile.kaapana_instance.instance_name }}</p>
        </v-col>
      </v-row> -->
      <v-row>
        <p> Participating Federated Permission Profiles:</p>
      </v-row>
      <v-row
        v-for="participating_fed_profile in federation.participating_federated_permission_profiles"
        :key="participating_fed_profile.federated_permission_profile_id"
      >
        <FederatedPermissionProfile
          :fed_perm_profile="federation.owner_federated_permission_profile"
        ></FederatedPermissionProfile>
      </v-row>
    </v-card-text>
  </v-card>
</template>
  
  <script>
  
  import kaapanaApiService from "@/common/kaapanaApi.service";
  
  import FederatedPermissionProfile from "@/components/FederatedPermissionProfile.vue";
  
  export default {
    components: {
      FederatedPermissionProfile,
    },

    name: 'FederatedPermissionProfile',

    data: () => ({
    }),

    props: {
      fed_perm_profile: {
        type: Object,
        required: true
      },
    },

    mounted () {
      this.printFed()
    },

    watch: {
    },

    computed: {
    },

    methods:{
      printFed() {
        console.log("fed_perm_profile: ", this.fed_perm_profile)
      }
    }
  }
  </script>
  
  <!-- Add "scoped" attribute to limit CSS to this component only -->
  <style scoped lang="scss">
  
  
  </style>
  