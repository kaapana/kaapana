<template>
  <div id="app">
    <v-app id="inspire">
      <notifications position="bottom right" width="20%" :duration="5000" />
      <v-navigation-drawer clipped v-model="drawer" app mobile-breakpoint="0">
        <v-list dense>
          <v-list-item :to="'/'">
            <v-list-item-icon>
              <v-icon>mdi-home</v-icon>
            </v-list-item-icon>
            <v-list-item-content>
              <v-list-item-title>Home</v-list-item-title>
            </v-list-item-content>
          </v-list-item>
          <v-list-group prepend-icon="mdi-gamepad-variant" :value="true">
            <template v-slot:activator>
              <v-list-item-title>Workflows</v-list-item-title>
            </template>
            <!-- WORKFLOWS -->
            <v-list-item v-for="([title, icon, to], i) in workflowsList" :key="i" :to="to" :value="to"
              v-if="isAuthenticated && _checkAuthR(policyData, to, currentUser)">
              <v-list-item-action></v-list-item-action>
              <v-list-item-title>{{ title }}</v-list-item-title>
              <v-list-item-icon>
                <v-icon>{{ icon }}</v-icon>
              </v-list-item-icon>
            </v-list-item>
          </v-list-group>
          <v-list-group
            :prepend-icon="section.icon"
            v-if="
              isAuthenticated &&
              checkAuthSection(policyData, section, currentUser)
            "
            v-for="(section, sectionKey) in externalWebpages"
            :key="section.id"
          >
            <template v-slot:activator>
              <v-list-item-title>{{ section.label }}</v-list-item-title>
            </template>
            <v-list-item v-if="section.subSections &&
        _checkAuthR(policyData, subSection.linkTo, currentUser)
        " v-for="(subSection, subSectionKey) in section.subSections" :key="subSection.id" :to="{
        name: 'ew-section-view',
        params: { ewSection: sectionKey, ewSubSection: subSectionKey },
      }">
              <v-list-item-action></v-list-item-action>
              <v-list-item-title v-text="subSection.label"></v-list-item-title>
            </v-list-item>
          </v-list-group>
          <!-- EXTENSIONS -->
          <v-list-item
            :to="'/extensions'"
            v-if="
              isAuthenticated &&
              _checkAuthR(policyData, '/extensions', currentUser)
            "
          >
            <v-list-item-action>
              <!-- <v-icon>mdi-view-comfy</v-icon> -->
              <!-- <v-icon>mdi-toy-brick-plus</v-icon> -->
              <v-icon>mdi-puzzle</v-icon>
            </v-list-item-action>
            <v-list-item-content>
              <v-list-item-title>Extensions</v-list-item-title>
            </v-list-item-content>
            <v-list-item-icon></v-list-item-icon>
          </v-list-item>
        </v-list>
      </v-navigation-drawer>
      <v-app-bar color="primary" dark dense clipped-left app>
        <v-app-bar-nav-icon @click.stop="drawer = !drawer"></v-app-bar-nav-icon>
        <v-toolbar-title>{{ commonData.name }}</v-toolbar-title>
        <v-spacer></v-spacer>
        <v-menu v-if="isAuthenticated" :close-on-content-click="false" :nudge-width="200" offset-x="offset-x">
          <template v-slot:activator="{ on }">
            <v-btn v-on="on" icon="icon">
              <v-icon>mdi-account-circle</v-icon>
            </v-btn>
          </template>
          <v-card>
            <v-list>
              <v-list-item>
                <v-list-item-content>
                  <v-list-item-title>{{ currentUser.username }}
                    <p>Welcome back!</p>
                  </v-list-item-title>
                </v-list-item-content>
              </v-list-item>
              <v-list-item>
                <Settings></Settings>
              </v-list-item>
              <v-list-item>
                <v-switch label="Dark mode" hide-details v-model="settings.darkMode"
                  @change="(v) => changeMode(v)"></v-switch>
              </v-list-item>
            </v-list>
            <v-card-actions>
              <v-spacer></v-spacer>
              <v-btn icon="icon" @click="logout()">
                <v-icon>mdi-exit-to-app</v-icon>
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-menu>
      </v-app-bar>
      <v-main id="v-main-content">
        <router-view></router-view>
      </v-main>
      <v-footer color="primary" app inset>
        <span class="white--text">
          &copy; DKFZ 2018 - DKFZ 2024 | {{ commonData.version }}
        </span>
      </v-footer>
    </v-app>
  </div>
</template>

<script lang="ts">
import Vue from "vue";
import request from "@/request";
import kaapanaApiService from "@/common/kaapanaApi.service";

import { mapGetters } from "vuex";
import { LOGIN, LOGOUT, CHECK_AUTH } from "@/store/actions.type";
import {
  CHECK_AVAILABLE_WEBSITES,
  LOAD_COMMON_DATA,
  GET_POLICY_DATA,
} from "@/store/actions.type";
import Settings from "@/components/Settings.vue";
import IdleTracker from "@/components/IdleTracker.vue";
import { settings } from "@/static/defaultUIConfig";
import { checkAuthR } from "@/utils/utils.js";

export default Vue.extend({
  name: "App",
  components: { Settings, IdleTracker },
  data: () => ({
    drawer: true,
    federatedBackendAvailable: false,
    settings: settings,
  }),
  created() {
    this.$store.watch(
      () => this.$store.getters["isIdle"],
      (newValue, oldValue) => {
        if (newValue) {
          this.onIdle();
        }
      }
    );
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
  methods: {
    _checkAuthR(policyData: any, endpoint: string, currentUser: any): boolean {
      "Check if the user has a role that authorizes him to access the requested endpoint";
      return checkAuthR(policyData, endpoint, currentUser);
    },
    checkAuthSection(policyData: any, section: any, currentUser: any): boolean {
      "Check if the user has a role that grants access to any subsection of the section";
      let endpoints = Object.values(section.subSections).map(
        (subsection: any) => subsection.linkTo
      );
      return endpoints.some((endpoint: string) =>
        this._checkAuthR(policyData, endpoint, currentUser)
      );
    },
    changeMode(v: boolean) {
      this.settings["darkMode"] = v;
      localStorage["settings"] = JSON.stringify(this.settings);
      this.$vuetify.theme.dark = v;
    },
    login() {
      this.$store
        .dispatch(LOGIN)
        .then(() => this.$router.push({ name: "home" }));
    },
    logout() {
      this.$store.dispatch(LOGOUT);
    },
    onIdle() {
      this.$store.dispatch(LOGOUT).then(() => {
        this.$router.push({ name: "" });
      });
    },
  },
  beforeCreate() {
    this.$store.dispatch(CHECK_AVAILABLE_WEBSITES);
    this.$store.dispatch(LOAD_COMMON_DATA);
    this.$store.dispatch(GET_POLICY_DATA);
    if (!localStorage["settings"]) {
      localStorage["settings"] = JSON.stringify(settings);
    }
  },
  mounted() {
    this.settings = JSON.parse(localStorage["settings"]);
    this.$vuetify.theme.dark = this.settings["darkMode"];
    request
      .get("/kaapana-backend/get-traefik-routes")
      .then((response: { data: {} }) => {
        this.federatedBackendAvailable = kaapanaApiService.checkUrl(
          response.data,
          "/kaapana-backend"
        );
      })
      .catch((error: any) => {
        console.log("Something went wrong with traefik", error);
      });
  },
});
</script>

<style lang="scss">
#app {
  font-family: "Avenir", Helvetica, Arial, sans-serif;
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  //text-align: center;
  font-size: 14px;
  line-height: 1.42857143;
  color: #333;
}

.kaapana-iframe-container-side-navigation {
  // 105px: Calculated by substracting the height of the whole screen by the hight of the embedded iframe.
  height: calc(100vh - 105px);
}

.kapaana-side-navigation {
  min-height: calc(100vh - 81px);
}

.v-item-group.v-bottom-navigation {
  border-bottom-width: 1px;
  border-bottom-style: solid;
  border-bottom-color: rgba(0, 0, 0, 0.12);
  -moz-box-shadow: none !important;
  -webkit-box-shadow: none !important;
  box-shadow: none !important;
}

@media (min-width: 2100px) {
  .container--fluid {
    max-width: 2100px !important;
  }
}
</style>
