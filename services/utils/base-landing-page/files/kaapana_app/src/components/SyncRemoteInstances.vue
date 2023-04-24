<template>
  <v-btn @click="doSyncing()" color="primary" small outlined rounded>
    sync remotes
    <!-- v-icon color="primary" dark="dark" x-large="x-large">mdi-sync-circle</v-icon -->
  </v-btn>
  <!-- v-btn @click="doSyncing()" small icon>
    <v-icon color="primary" dark >mdi-sync-circle</v-icon>
  </v-btn -->
</template>

<script>
import kaapanaApiService from "@/common/kaapanaApi.service";

export default {
  name: "SyncRemoteInstances",
  
  data: () => ({
  }),

  mounted () {
  },

  props: {
  },

  methods: {
    doSyncing() {
      this.checkForRemoteUpdates()
    },
    checkForRemoteUpdates() {
      console.log('checking remote')
      kaapanaApiService
        .federatedClientApiGet("/check-for-remote-updates")
        .then((response) => {
          this.$notify({
            type: 'success',
            title: 'Successfully checked for remote updates',
            // text: 
          }),
          this.$emit('refreshRemoteFromSyncing')
        })
        .catch((err) => {
          console.log(err);
        });
    },
  }
}

</script>