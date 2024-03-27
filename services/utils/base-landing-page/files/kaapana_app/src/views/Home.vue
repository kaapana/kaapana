<template lang="pug">
  .kaapana-intro-header
    IdleTracker
    v-container(grid-list-lg text-xs-center fluid)
      div(v-if="isAuthenticated")
        v-layout(row='')
          v-flex(sm9)
            v-layout(row='')
              v-flex(sm12)
                KaapanaWelcome
              v-flex(sm12)
                v-layout(row='', wrap='')
                  v-flex(d-flex, class="sm12")
                    v-card(width='100%')
                      v-card-title
                        //- span.kaapana-headline Workflows&nbsp;
                        //- v-icon(large) mdi-gamepad-variant
                      v-card-text
                        v-layout(row='', wrap='')
                          v-flex.justify-center(v-for="([title, icon, to], i) in workflowsList" :key="i" :to="to" :value="to")
                            v-card(:to="to" elevation=0 v-if="_checkAuthR(policyData, to, currentUser)")
                              v-card-title.justify-center
                                v-icon(x-large) {{ icon }}
                              v-card-text
                                span {{ title }}
                          v-flex
                            v-card(to="/extensions" elevation=0 v-if="_checkAuthR(policyData, '/extensions', currentUser)")
                              v-card-title.justify-center
                                v-icon(x-large) mdi-puzzle
                              v-card-text
                                span Extensions
            v-layout(v-if="_checkAuthR(policyData, '/grafana', currentUser)")
              v-flex(sm4)
                <iframe src="/grafana/d-solo/adadsdasd/kubernetes?orgId=1&panelId=72" width="100%" height="auto" frameborder="0"></iframe>
              v-flex(sm4)
                <iframe src="/grafana/d-solo/adadsdasd/kubernetes?orgId=1&panelId=55" width="100%" height="auto" frameborder="0"></iframe>
              v-flex(sm4)
                <iframe src="/grafana/d-solo/adadsdasd/kubernetes?orgId=1&panelId=44" width="100%" height="auto" frameborder="0"></iframe>
          v-flex(sm3)
            Dashboard(:seriesInstanceUIDs="seriesInstanceUIDs" :fields="this.settings.landingPage")
      div(v-else)
        v-layout(align-center justify-center row fill-height)
          v-flex(sm12)
            v-card
              v-card-text.text-xs-left
                h1 Thank you for visiting us. We hope to see you again!
                p
                  | In order to log in again, please reload the page or 
                  a(@click="reloadPage()") click here
                  | .
</template>

<script>
import IdleTracker from "@/components/IdleTracker.vue"
import { Component, Vue } from "vue-property-decorator";
import { mapGetters } from "vuex";
import KaapanaWelcome from "@/components/WelcomeViews/KaapanaWelcome.vue";
import Dashboard from "@/components/Dashboard.vue";
import { loadPatients } from "../common/api.service";
import { checkAuthR } from "@/utils/utils.js";

export default Vue.extend({
  data() {
    return {
      seriesInstanceUIDs: [],
    };
  },
  components: {
    KaapanaWelcome,
    Dashboard,
    IdleTracker,
  },
  computed: {
    ...mapGetters([
      "currentUser",
      "isAuthenticated",
      "externalWebpages",
      "workflowsList",
      "commonData",
      "policyData",
    ]),
  },
  created() {
    this.settings = JSON.parse(localStorage["settings"]);
    loadPatients({
      structured: false,
      query: { bool: { must: ["", { query_string: { query: "*" } }] } },
    })
      .then((data) => {
        this.seriesInstanceUIDs = data;
      })
      .catch((e) => {
        this.message = e;
      });
  },
  methods: {
    reloadPage() {
      window.location.reload();
    },
    _checkAuthR(policyData, endpoint, currentUser) {
      return checkAuthR(policyData, endpoint, currentUser);
    },
  },
});
</script>

<style lang="scss">
.kaapana-page-link {
  color: black;
  text-decoration: none;
}

.kaapana-headline {
  font-size: 24px;
  font-weight: 300px;
}

.kaapana-intro-header {
  text-align: center;
  background-size: cover;
}
</style>
