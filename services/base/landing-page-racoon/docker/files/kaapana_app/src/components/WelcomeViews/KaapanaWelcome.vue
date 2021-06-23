<template lang="pug">
  v-layout(row='', wrap='')
    v-flex.text-xs-left(sm8, d-flex)
      v-card.kaapana-opacity-card
        v-card-text.text-xs-left
          v-layout(row='', wrap='')
            h3.text-center(style={'font-size': '45px','width': '100%', 'color': 'black','margin-bottom': '20px', 'margin-top': '20px'}) {{ commonData.infoText }}
            img(src='../../assets/racoon_highres.png', alt='Vuetify', width='100%')
            h3.text-center(style={'font-size': '45px','width': '100%', 'color': 'black','margin-bottom': '20px', 'margin-top': '20px'}) {{ 'For RACOON' }}
    v-flex.text-xs-left(sm4 d-flex)
      v-card.kaapana-opacity-card(width='100%')
        v-card-text.text-xs-left
          span.kaapana-headline Contact us
          hr.my-2
          v-layout(row='', wrap='')
            v-flex(xs12, py-1)
              v-icon mdi-email
              |&nbsp;
              a(href="https://join.slack.com/t/kaapana/shared_invite/zt-hilvek0w-ucabihas~jn9PDAM0O3gVQ/") join us on Slack
          br
          span.kaapana-headline Project coordinator
          hr.my-2
          div(style={'margin': '14px'})
            img(src='../../assets/num.png', alt='Vuetify', width='100%')
</template>

<script>
import { mapGetters } from "vuex";

export default {
  name: 'KaapanaWelcome',
  props: {

  },
  computed: {
    ...mapGetters(["commonData"])
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

.iframe-window {
  border: none;
}

</style>
