
<template lang="pug">
  v-layout(row='', wrap='')
    v-flex.text-xs-left(sm8, d-flex)
      v-card.kaapana-opacity-card
        v-card-text.text-xs-left
          v-layout(row='', wrap='')
            v-flex(xs3, py-1)
              div(style={'margin': '9px'})
                img(src='../../assets/logo.png', alt='Vuetify', width='100%')
            v-flex(xs9, py-1)
              span.kaapana-headline(style={'line-height': '55px','font-size': '50px'})
                | Welcome 
                br 
                | to the
                br 
                | {{ commonData.name }}
            v-flex(xs12, py-1)
              h3.text-left(style={'font-size': '18px'}) {{ commonData.infoText }}
            v-flex(xs12, py-1) 
              h3.text-left(style={'font-size': '18px', 'color': 'red', 'margin-top': '10px'}) {{ commonData.disclaimer }}
    v-flex.text-xs-left(sm4 d-flex)
      v-card.kaapana-opacity-card(width='100%')
        v-card-text.text-left
          span.kaapana-headline Contact us
          hr.my-2
          v-layout(row='', wrap='')
            v-flex(xs12, py-1)
              v-icon mdi-email 
              |&nbsp;
              a(href="mailto:jip-service@dkfz-heidelberg.de?subject=JIP%20Support%20Question") jip-service@dkfz-heidelberg.de
            //- v-flex(xs12, py-1)
            //-   v-icon fab fa-slack
            //-   |&nbsp;
            //-   a(href="https://dktk-jip.slack.com/" target='_blank') jip-dktk
          br
          span.kaapana-headline Project coordinator
          hr.my-2
          div(style={'margin': '14px'})
            img(src='../../assets/160512_DKTK-Platine_single_combined.png', alt='Vuetify', width='100%')
</template>

<script>
import { mapGetters } from "vuex";

export default {
  name: 'JIPWelcome',
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
