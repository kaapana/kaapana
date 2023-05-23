
<template lang="pug"> 
div(:class="fullSize ? (navigationMode ? 'kaapana-iframe-container-side-navigation' : 'kaapana-iframe-container-top-navigation') : ''")
  iframe(ref="iframe" :width="width" :height="height" :style="customStyle" :class="fullSize ? (navigationMode ? 'kapaana-side-navigation' : 'kapaana-top-navigation') : ''" class="no-border" :src="iFrameUrl" @load="setIframeUrl(this)")
</template>

<script>
export default {
  name: 'IFrameWindow',
  data: function () {
    return {
      trackedUrl: '',
      navigationMode: false
    }
  },
  props: {
    iFrameUrl: {
      type: String,
      required: true
    },
    fullSize: {
      type: Boolean,
      default: true
    },
    width: {
      type: String, 
      default: '100%',
    },
    height: {
      type: String, 
      default: '100%',
    },
    customStyle: {
      type: String,
      default: ''
    }
  },
  methods:{
    refreshIFrame: function(event){
      this.$refs.iframe.src = this.trackedUrl
    },
    setIframeUrl: function(url){
      // would be nices to react directly on changes in the settings
      this.navigationMode = !document.getElementsByClassName("v-bottom-navigation").length > 0
      this.trackedUrl = this.$refs.iframe.contentWindow.location
    },
    getIframeUrl: function(){
      return this.$refs.iframe.contentWindow.location
    }
  }
}
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped lang="scss">

.no-border {
  border: none;
}

</style>
