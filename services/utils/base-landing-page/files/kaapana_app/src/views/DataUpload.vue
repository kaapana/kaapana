<template lang="pug">
  .dropzone
    v-container(grid-list-lg text-left)
      upload(labelIdle="Drop files that shoud be available in workflows here... Attention! In case you want to upload image data you need to first upload them here in a zip file and then execute the dicom-upload workflow!")

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
