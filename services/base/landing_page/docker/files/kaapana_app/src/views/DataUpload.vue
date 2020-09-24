<template lang="pug">
  .dropzone
    v-container(grid-list-lg text-left)
      div
        upload(targetFolder="dicoms", labelIdle="Drop zip with dicoms files here...")

</template>

<script lang="ts">
// upload(targetFolder="doccano", labelIdle="Drop your doccano project here...")
import Vue from 'vue';
import request from '@/request';
import { mapGetters } from "vuex";
import kaapanaApiService from '@/common/kaapanaApi.service';
import Upload from "@/components/Upload.vue";

export default Vue.extend({
  components: {
    Upload
  },
  data: () => ({
   
  }),
  mounted() {

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
