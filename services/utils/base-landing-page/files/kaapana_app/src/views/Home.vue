<template lang="pug">
  .kaapana-intro-header
    .kaapana-intro-image
      v-container(grid-list-lg text-xs-center)
        div(v-if="isAuthenticated")
          v-layout(row='', wrap='')
            v-flex(sm12)
              KaapanaWelcome
            v-flex(sm12)
              v-layout(row='', wrap='')
                v-flex.text-left(v-if='section.roles.indexOf(currentUser.role) > -1' v-for='(section, sectionKey) in this.externalWebpages', :key='section.id', d-flex, v-bind:class="{ sm8: sectionKey=='system', sm4: sectionKey!='system'}")
                  v-card.kaapana-opacity-card
                    v-card-title.kaapana-card-prop
                      span.kaapana-headline {{section.label}}
                      v-spacer
                      v-icon(size='35px') {{section.icon}}
                    v-card-text.kaapana-card-prop
                      p {{section.description}}
                      v-chip.kaapana-chips(v-for='(subSection, subSectionKey) in section.subSections', :key='subSection.id' color="jipgreen")
                        router-link.kaapana-page-link(:to="{ name: 'ew-section-view', params: { ewSection: sectionKey, ewSubSection: subSectionKey }}") {{subSection.label}}
        div(v-else)
          v-layout(align-center justify-center row fill-height)
            v-flex(sm12)
              v-card.kaapana-opacity-card
                v-card-text.text-xs-left
                  h1 Thank you for visiting us. We hope to see you again!
                  p
                    | In order to log in again, please reload the page or 
                    a(@click="reloadPage()") click here
                    | .
</template>




<script lang="ts">

import { Component, Vue } from 'vue-property-decorator';
import { mapGetters } from "vuex";
import KaapanaWelcome from "@/components/WelcomeViews/KaapanaWelcome.vue";

@Component({
  components: {
    KaapanaWelcome
  },
  computed: {
    ...mapGetters(["currentUser", "isAuthenticated", "externalWebpages",  "commonData"])
  },
  methods: {
    reloadPage() {
      window.location.reload(true)
    }
  }
})

export default class Home extends Vue {}
</script>

<style lang="scss">
</style>
