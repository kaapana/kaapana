
<template lang="pug">
  v-layout(row='', wrap='')
    v-flex.text-xs-left(sm8, d-flex)
      v-card.kaapana-opacity-card
        v-card-text.text-xs-left
          v-layout(row='', wrap='')
            v-flex(xs12, py-1)
              div(style={'margin': '9px', 'margin-top': '50px'})
                img(src='../../assets/tfda_logo.png', alt='Vuetify', width='100%')
              div(style={'margin': '9px', 'margin-top': '50px'})
                img(src='../../assets/dkfz_logo.jpeg', alt='Vuetify', width='50%') 
              div(style={'margin': '9px', 'margin-top': '50px'})
                img(src='../../assets/cispa_logo.jpeg', alt='Vuetify', width='50%')
    v-flex.text-xs-left(sm4 d-flex)
      v-card.kaapana-opacity-card(width='100%')
        v-card-text.text-xs-left
          span.kaapana-headline About TFDA
          hr.my-2
          v-layout(row='', wrap='')
            v-flex(xs12, py-1)
              
              |&nbsp;
              //a(href="mailto:kaapana@dkfz-heidelberg.de?subject=kaapana%20Support%20Question") kaapana@dkfz-heidelberg.de
              To To solve future grand challenges, data, computational power and analytics expertise need to be brought together at unprecedented scale. The need for data has become even larger in the context of recent advances in machine learning. Therefore, data-centric digital systems commonly exhibit a strong tendency towards centralized structures. While data centralization can greatly facilitate analysis, it also comes with several intrinsic disadvantages and threats not only from a technical but more importantly also from a legal, political and ethical perspective. Rooting in sophisticated security or trust requirements, overcoming these issues is cumbersome and time consuming. As a consequence, many research projects are substantially hindered, fail or are simply not addressed. In this interdisciplinary project we aim at facilitating the implementation of decentralized, cooperative data analytics architectures within and beyond Helmholtz by addressing the most relevant issues in such scenarios. Trustworthy Federated Data Analytics (TFDA) will facilitate bringing the algorithms to the data in a trustworthy and regulatory compliant way instead of going a data-centric way. TFDA will address the technical, methodical and legal aspects when ensuring trustworthiness of analysis and transparency regarding the analysis in- and outputs without violating privacy constraints. To demonstrate applicability and to ensure the adaptability of the methodological concepts, we will validate our developments for the usage in medical research with the use case “Federated radiation therapy study” before disseminating the results.
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
