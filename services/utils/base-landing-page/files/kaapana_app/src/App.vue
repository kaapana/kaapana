<template>
  <div id="app">
    <v-app id="inspire">
      <notifications position="bottom right" width="20%" />
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
          <!-- top navigation -->
          <v-list-item
            v-if="settings.navigationMode && isAuthenticated"
            :to="'/workflows'"
          >
            <v-list-item-action>
              <v-icon>mdi-gamepad-variant</v-icon>
            </v-list-item-action>
            <v-list-item-content>
              <v-list-item-title>Workflows</v-list-item-title>
            </v-list-item-content>
            <v-list-item-icon></v-list-item-icon>
          </v-list-item>
          <v-list-item
            v-if="settings.navigationMode && isAuthenticated"
            :to="{
              name: 'ew-section-view',
              params: { ewSection: 'store', ewSubSection: 'minio' },
            }"
          >
            <v-list-item-action>
              <v-icon>mdi-palette-advanced</v-icon>
            </v-list-item-action>
            <v-list-item-content>
              <v-list-item-title>Advanced</v-list-item-title>
            </v-list-item-content>
            <v-list-item-icon></v-list-item-icon>
          </v-list-item>
          <!-- Default navigation mode -->
          <v-list-group
            v-if="!settings.navigationMode"
            prepend-icon="mdi-gamepad-variant"
            :value="true"
          >
            <template v-slot:activator>
              <v-list-item-title>Workflows</v-list-item-title>
            </template>
            <v-list-item
              v-for="([title, icon, to], i) in workflowsList"
              :key="i"
              :to="to"
              :value="to"
              v-if="isAuthenticated"
            >
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
              !settings.navigationMode &&
              isAuthenticated &&
              section.roles.indexOf(currentUser.role) > -1
            "
            v-for="(section, sectionKey) in externalWebpages"
            :key="section.id"
          >
            <template v-slot:activator>
              <v-list-item-title>{{ section.label }}</v-list-item-title>
            </template>
            <v-list-item
              v-if="section.subSections"
              v-for="(subSection, subSectionKey) in section.subSections"
              :key="subSection.id"
              :to="{
                name: 'ew-section-view',
                params: { ewSection: sectionKey, ewSubSection: subSectionKey },
              }"
            >
              <v-list-item-action></v-list-item-action>
              <v-list-item-title v-text="subSection.label"></v-list-item-title>
            </v-list-item>
          </v-list-group>
          <v-list-item :to="'/extensions'" v-if="isAuthenticated">
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
        <v-menu
          v-if="isAuthenticated"
          :close-on-content-click="false"
          :nudge-width="200"
          offset-x="offset-x"
        >
          <template v-slot:activator="{ on }">
            <v-btn v-on="on" icon="icon">
              <v-icon>mdi-account-circle</v-icon>
            </v-btn>
          </template>
          <v-card>
            <v-list>
              <v-list-item>
                <v-list-item-content>
                  <v-list-item-title
                    >{{ currentUser.username }}
                    <p>Welcome back!</p>
                  </v-list-item-title>
                </v-list-item-content>
              </v-list-item>
              <v-list-item>
                <Settings></Settings>
              </v-list-item>
              <v-list-item>
                <v-switch
                  label="Dark mode"
                  hide-details
                  v-model="settings.darkMode"
                  @change="(v) => changeMode(v)"
                ></v-switch>
              </v-list-item>
              <v-list-item>
                <v-switch
                  label="Navigation"
                  hide-details
                  v-model="settings.navigationMode"
                  @change="(v) => changeNavigation(v)"
                ></v-switch>
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
        <v-container class="router-container pa-0" fluid fill-height>
          <v-layout align-start="align-start">
            <v-flex text-xs="text-xs">
              <div v-if="settings.navigationMode">
                <v-bottom-navigation
                  v-if="workflowNavigation && drawer"
                  color="primary"
                  :elevation="0"
                  inset
                  mode="shift"
                >
                  <v-btn
                    v-for="([title, icon, to], i) in workflowsList"
                    :key="i"
                    :to="to"
                    :value="to"
                  >
                    <v-icon>{{ icon }}</v-icon>
                    {{ title }}
                  </v-btn>
                </v-bottom-navigation>
                <v-bottom-navigation
                  v-if="advancedNavigation && drawer"
                  color="primary"
                  :elevation="0"
                  inset
                  mode="shift"
                >
                  <v-menu
                    offset-y
                    v-for="(section, sectionKey) in externalWebpages"
                    :key="section.id"
                  >
                    <template v-slot:activator="{ on, attrs }">
                      <v-btn v-bind="attrs" v-on="on">
                        <v-icon>{{ section.icon }}</v-icon>
                        {{ section.label }}
                      </v-btn>
                    </template>
                    <v-list>
                      <v-list-item
                        v-for="(
                          subSection, subSectionKey
                        ) in section.subSections"
                        :key="subSection.id"
                        :value="subSection.id"
                        :to="{
                          name: 'ew-section-view',
                          params: {
                            ewSection: sectionKey,
                            ewSubSection: subSectionKey,
                          },
                        }"
                      >
                        <v-list-item-title>{{
                          subSection.label
                        }}</v-list-item-title>
                      </v-list-item>
                    </v-list>
                  </v-menu>
                </v-bottom-navigation>
              </div>
              <router-view></router-view>
            </v-flex>
          </v-layout>
        </v-container>
      </v-main>
      <v-footer color="primary" app inset>
        <span class="white--text">
          &copy; DKFZ 2018 - DKFZ 2023 | {{ commonData.version }}
        </span>
      </v-footer>
    </v-app>
  </div>
</template>

<script lang="ts">
/* eslint-disable */

import Vue from "vue";
import request from "@/request";
import kaapanaApiService from "@/common/kaapanaApi.service";

import { mapGetters } from "vuex";
import { LOGIN, LOGOUT, CHECK_AUTH } from "@/store/actions.type";
import {
  CHECK_AVAILABLE_WEBSITES,
  LOAD_COMMON_DATA,
} from "@/store/actions.type";
import Settings from "@/components/Settings.vue";
import { settings } from "@/static/defaultUIConfig";

export default Vue.extend({
  name: "App",
  components: { Settings },
  data: () => ({
    drawer: true,
    federatedBackendAvailable: false,
    settings: settings,
    workflowsList: [
      ["Data Upload", "mdi-cloud-upload", "/data-upload"],
      ["Datasets", "mdi-view-gallery-outline", "/datasets"],
      ["Workflow Execution", "mdi-play", "/workflow-execution"],
      ["Workflow List", "mdi-clipboard-text-outline", "/workflows"],
      ["Workflow Results", "mdi-chart-bar-stacked", "/results-browser"],
      ["Instance Overview", "mdi-vector-triangle", "/runner-instances"],
      ["Pending Applications", "mdi-timer-sand", "/pending-applications"],
    ],
  }),
  computed: {
    ...mapGetters([
      "currentUser",
      "isAuthenticated",
      "externalWebpages",
      "commonData",
    ]),
    workflowNavigation() {
      let routerPath = [];
      for (const workflow of this.workflowsList) {
        routerPath.push(workflow[2]);
      }
      return routerPath.includes(this.$route.path);
    },
    advancedNavigation() {
      let routerPath = ["/", "/data-upload", "/extensions"];
      for (const workflow of this.workflowsList) {
        routerPath.push(workflow[2]);
      }
      return !routerPath.includes(this.$route.path);
    },
  },
  methods: {
    changeMode(v: boolean) {
      this.settings["darkMode"] = v;
      localStorage["settings"] = JSON.stringify(this.settings);
      this.$vuetify.theme.dark = v;
    },
    changeNavigation(v: boolean) {
      this.settings["navigationMode"] = v;
      localStorage["settings"] = JSON.stringify(this.settings);
    },
    login() {
      this.$store
        .dispatch(LOGIN)
        .then(() => this.$router.push({ name: "home" }));
    },
    logout() {
      this.$store.dispatch(LOGOUT);
    },
  },
  beforeCreate() {
    this.$store.dispatch(CHECK_AVAILABLE_WEBSITES);
    this.$store.dispatch(LOAD_COMMON_DATA);
    if (!localStorage["settings"]) {
      localStorage["settings"] = JSON.stringify(settings);
    }
  },
  mounted() {
    this.settings = JSON.parse(localStorage["settings"]);
    this.$vuetify.theme.dark = this.settings["darkMode"];
    request
      .get("/traefik/api/http/routers")
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
  onIdle() {
    console.log("checking", this.$store.getters.isAuthenticated);
    this.$store
      .dispatch(CHECK_AUTH)
      .then(() => {
        console.log("still online");
      })
      .catch((err: any) => {
        console.log("reloading");
        location.reload();
        // this.$router.push({ name: 'home' });
        // this.$store.dispatch(LOGOUT).then(() => {
        //   this.$router.push({ name: 'home' });
        // });
      });
  },
});
</script>

<style lang="scss">
$kaapana-blue: rgba(0, 71, 156, 0.95);
$kaapana-green: #ff7a20;

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

.router-container {
  //padding: 12px
}

// Example of colors
.kaapana-blue {
  color: $kaapana-blue;
}

.kaapana-iframe-container-side-navigation {
  height: calc(100vh - 105px); // 105px: Calculated by substracting the height of the whole screen by the hight of the embedded iframe.
}

.kaapana-iframe-container-top-navigation {
  height: calc(100vh - 105px - 56px);
}

.kapaana-side-navigation {
  min-height: calc(100vh - 81px);
}

.kapaana-top-navigation {
  min-height: calc(100vh - 81px - 56px);
}

.kaapana-headline {
  font-size: 24px;
  font-weight: 300px;
}

.kaapana-page-link {
  color: black;
  text-decoration: none;
}

.kaapana-card-prop {
  padding: 10px;
}

.kaapana-intro-header {
  position: relative;
}

// .kaapana-intro-header {
//   min-height: calc(100vh - 105px);
// }
// .kaapana-intro-header .kaapana-intro-image {
//   padding-top: 10px;
//   padding-bottom: 10px;
//   //color: white;
//   text-align: center;
//   //background: DeepSkyBlue;
//   background-size: cover;
// }

.kaapana-opacity-card {
  //background: rgba(255, 255, 255, 0.87) !important
}

.pa-0 {
  padding: 0;
}
</style>
