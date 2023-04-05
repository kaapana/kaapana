<template>
  <v-btn @click="checkForRemoteUpdates()" small plain>
    sync remotes
    <!-- v-icon color="primary" dark="dark" x-large="x-large">mdi-sync-circle</v-icon -->
  </v-btn>
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
    remote: {
      type: Boolean,
      required: true,
    },
    clientinstance: {
      type: Object,
      required: true
    }
  },

  methods: {
    checkForRemoteUpdates() {
      console.log('checking remote')
      kaapanaApiService
        .federatedClientApiGet("/check-for-remote-updates")
        .then((response) => {
          this.$notify({
            type: 'success',
            title: 'Successfully checked for remote updates',
            // text: 
          })
          this.$emit('refreshView')
        })
        .catch((err) => {
          console.log(err);
        });
    },
  }
}

</script>