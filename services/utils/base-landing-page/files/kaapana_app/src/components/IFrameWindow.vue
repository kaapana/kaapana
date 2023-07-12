
<template lang="pug"> 
div(:class="fullSize ? (navigationMode ? 'kaapana-iframe-container-side-navigation' : 'kaapana-iframe-container-top-navigation') : ''")
  v-progress-circular(:class="cycleClass" :style="customStyle" indeterminate color="primary")
  iframe(ref="iframe" :width="width" :height="height" :style="customStyle" :class="[isLoading? opacity : '', fullSize ? (navigationMode ? 'kapaana-side-navigation' : 'kapaana-top-navigation') : '']" class="no-border" :src="iFrameUrl" @load="setIframeUrl(this)")
</template>

<script>
export default {
  name: 'IFrameWindow',
  data: function () {
    return {
      trackedUrl: '',
      navigationMode: false,
      isLoading: true,
      cycleClass: 'cycle-bar',
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
  watch: {
    iFrameUrl () {
      console.log('watch')
      this.cycleClass = "cycle-bar"
    }
  },
  mounted() {
      this.$refs.iframe.onload = () => {
        this.isLoading = false
        this.cycleClass = "hide-cycle-bar"
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

.opacity {
  opacity: 0.2;
}

.cycle-bar {
  position: fixed;
  margin: auto;
  top: 0;
  left: 0;
  bottom: 0;
  right: 0;
  z-index: 1000000;
}

.hide-cycle-bar {
  display: none;
}
</style>
