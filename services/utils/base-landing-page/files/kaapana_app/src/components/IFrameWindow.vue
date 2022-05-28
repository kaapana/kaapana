
<template lang="pug">
  iframe(ref="iframe" :width="width" :height="height" class="iframe-window" :src="iFrameUrl" @load="setIframeUrl(this)")
</template>

<script>

export default {
  name: 'IFrameWindow',
  data: function () {
    return {
      trackedUrl: ''
    }
  },
  props: {
    iFrameUrl: {
      type: String,
      required: true
    },
    width: {
      type: String, 
      default: '100%',
    },
    height: {
      type: String, 
      default: '100%',
    }
  },
  methods:{
    refreshIFrame: function(event){
      this.$refs.iframe.src = this.trackedUrl
    },
    setIframeUrl: function(url){
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

.iframe-window {
  border: none;
  min-height: calc(100vh - 105px);
}

</style>
