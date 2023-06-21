
<template lang="pug">
  v-layout(row='')
    v-flex.text-xs-left(sm8, d-flex)
      v-card
        v-card-text.text-xs-left
          v-layout
            v-flex(xs12, py-1)
              div(style={'margin': '9px', 'margin-top': '10px'})
                img(src='../../assets/img/kaapana.png', alt='Vuetify', width='35%')
    v-flex.text-xs-left(sm4 d-flex)
      v-card(column justify-space-between fill-height width='100%')
        v-card-text.text-xs-left()
          div
            h2 Welcome {{ currentUser.username }}!
            p Join us on Slack or drop us an email!
            hr.my-2
        v-card-text
          v-layout
            v-flex(xs6, py-1)
              a(href="https://join.slack.com/t/kaapana/shared_invite/zt-hilvek0w-ucabihas~jn9PDAM0O3gVQ", target="_blank")
                v-icon(x-large) mdi-slack
            v-flex(xs6, py-1)
              a(href="mailto:kaapana@dkfz-heidelberg.de?subject=kaapana%20Support%20Question")
                v-icon(x-large) mdi-email
</template>

<script>
import { mapGetters } from "vuex";

export default {
  name: 'KaapanaWelcome',
  props: {

  },
  computed: {
    ...mapGetters(["commonData", "currentUser"])
  },
  methods:{
    refreshIFrame: function(event){
      this.$refs.iframe.src = this.$refs.iframe.src
    }
  }
}
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped lang="scss">

</style>
