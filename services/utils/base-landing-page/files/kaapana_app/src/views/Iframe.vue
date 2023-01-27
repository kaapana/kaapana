
<template lang="pug">
  .kaapana-iframe-container(v-if="hasLoadedData")
    IFrameWindow(ref="foo" :iFrameUrl="getUrl" width="100%" height="100%")
    #overlay
      a(@click="refreshIFrame()")
        v-icon(color="white") mdi-refresh
      a(@click="openExternalPage()")
        v-icon(color="white") mdi-open-in-new
  
</template>


<script>
// @ is an alias to /src
import Vue from 'vue'
import { mapGetters } from "vuex";

import IFrameWindow from "@/components/IFrameWindow.vue";
export default {
  name: 'iframe-view',
  components: {
    IFrameWindow
  },
  data: function () {
    return {
      iFrameUrl: null
    }
  },
  computed: {
    ...mapGetters(["currentUser", "isAuthenticated", "externalWebpages"]),
    hasLoadedData () {
      // Or whatever criteria you decide on to represent that the
      // app state has finished loading.
      return this.externalWebpages !== null
    },
    getUrl: function () {
      var finalUrl = ''
      if (this.$route.name === 'iframe-view') {
        // TODO
      } else if (this.$route.name === 'ew-section-view') {
        // console.log('external', this.externalWebpages)
        finalUrl = this.externalWebpages[this.$route.params.ewSection].subSections[this.$route.params.ewSubSection].linkTo
      } else if (this.$route.name == 'security-iframe-view') {
        finalUrl = window.location.origin + window.location.href.substring(window.location.href.lastIndexOf('/security'));
      }
      return finalUrl
    }
  },
  methods: {
    refreshIFrame: function () {
      this.$refs.foo.refreshIFrame()
    },
    openExternalPage: function() {
      window.open(this.$refs.foo.getIframeUrl(), '_blank');
    }
  }
}
</script>

<style lang="scss">
#overlay {
  position: absolute;
  bottom: 40px;
  right: 40px;
  text-align: center;
  background-color: rgba(77, 77, 77, 0.466);
  padding: 2px;
  z-index: 2147483647;
}
#overlay > a {
  line-height: 0px;
}
#overlay > a > i {
  margin: 2px;
}
</style>
