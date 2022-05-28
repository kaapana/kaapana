<template lang="pug">
  .dropzone
    v-container(grid-list-lg text-left)
      div(v-if="supported")
        upload(targetFolder="dicoms", labelIdle="Drop zip with dicoms files here...")
      div(v-else)
        v-alert(color='red' type='info') The data upload is not supported in Firefox.

</template>

<script lang="ts">

import Vue from 'vue';
import { mapGetters } from "vuex";
import Upload from "@/components/Upload.vue";

export default Vue.extend({
  components: {
    Upload
  },
  data: () => ({
    supported: true,
  }),
  mounted() {
    const { userAgent } = navigator
    if (userAgent.includes('Firefox/')) {
      this.supported = false
    } else {
      this.supported = true
    }
  },
  computed: {
    ...mapGetters(['currentUser', 'isAuthenticated'])
  },
  methods: {
  }
})
</script>

<style lang="scss">
</style>
