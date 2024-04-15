<template lang="pug"> 
div(:class="fullSize ? 'kaapana-iframe-container-side-navigation' : ''")
  iframe(ref="iframe" :width="width" :height="height" :style="customStyle" :class="fullSize ? 'kapaana-side-navigation' : ''" class="no-border" :src="iFrameUrl" @load="setIframeUrl(this)")
</template>

<script>
export default {
  name: "IFrameWindow",
  data: function () {
    return {
      trackedUrl: "",
    };
  },
  props: {
    iFrameUrl: {
      type: String,
      required: true,
    },
    fullSize: {
      type: Boolean,
      default: true,
    },
    width: {
      type: String,
      default: "100%",
    },
    height: {
      type: String,
      default: "100%",
    },
    customStyle: {
      type: String,
      default: "",
    },
  },
  methods: {
    refreshIFrame: function (event) {
      this.$refs.iframe.src = this.trackedUrl;
    },
    setIframeUrl: function (url) {
      this.trackedUrl = this.$refs.iframe.contentWindow.location;
    },
    getIframeUrl: function () {
      return this.$refs.iframe.contentWindow.location;
    },
  },
  beforeRouteUpdate(to, from, next) {
    // This is needed for authorization when changing from one iFrame window to another.
    // Since this happens on the same route, beforeRoute navigation guards are not triggered.
    return guardRoute(to, from, next);
  },
};
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped lang="scss">
.no-border {
  border: none;
}
</style>
