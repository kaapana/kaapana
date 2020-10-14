
<template lang="pug">
  v-layout(row='', wrap='')
    v-flex.text-xs-left(sm8, d-flex)
      v-card.kaapana-opacity-card
        v-card-text.text-xs-left
          v-layout(row='', wrap='')
            v-flex(xs12, py-1)
              div(style={'margin': '9px', 'margin-top': '50px'})
                img(src='../../assets/kaapana.png', alt='Vuetify', width='100%')
            // v-flex(xs7, py-1)
            //   span.kaapana-headline(style={'line-height': '55px','font-size': '50px'})
            //     | Welcome 
            //     br 
            //     | to the
            //     br 
            //     | {{ commonData.name }}
            v-flex(xs12, py-1)
              h3.text-left(style={'font-size': '18px'}) {{ commonData.infoText }}
    v-flex.text-xs-left(sm4 d-flex)
      v-card.kaapana-opacity-card(width='100%')
        v-card-text.text-xs-left
          span.kaapana-headline Contact us
          hr.my-2
          v-layout(row='', wrap='')
            v-flex(xs12, py-1)
              v-icon mdi-email
              |&nbsp;
              a(href="mailto:kaapana@dkfz-heidelberg.de?subject=kaapana%20Support%20Question") kaapana@dkfz-heidelberg.de
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
