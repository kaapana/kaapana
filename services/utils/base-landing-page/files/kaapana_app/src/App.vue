<template>
  <div id="app">
    <v-app id="inspire">
      <notifications position="bottom right" width="20%" :duration="5000" />
      <v-navigation-drawer
          v-model="drawer" app mobile-breakpoint="0"
          :mini-variant.sync="mini"
          permanent
        >
        <div class="blue py-2 mb-5">
          <v-list-item class="px-2 pb-2">
            <router-link to="/" class="d-inline-block">
              <v-list-item-avatar>
                <v-img src="/favicon.ico" title="Kaapana"></v-img>
              </v-list-item-avatar>
            </router-link>

            <v-spacer></v-spacer>

            <v-btn icon @click.stop="mini = !mini" title="Collapse Sidebar">
              <v-icon>mdi-dock-left</v-icon>
            </v-btn>
            <About/>
            <v-menu
              v-if="isAuthenticated"
              :close-on-content-click="false"
              bottom left offset-y
            >
              <template v-slot:activator="{ on }">
                <v-btn v-on="on" icon="icon" title="User">
                  <v-icon>mdi-account-circle</v-icon>
                </v-btn>
              </template>
              <v-card>
                <v-list>
                  <v-list-item>
                    <v-list-item-avatar>
                      <v-icon>mdi-account-circle</v-icon>
                    </v-list-item-avatar>
                    <v-list-item-content>
                      <v-list-item-title>{{ currentUser.username }}</v-list-item-title>
                      <v-list-item-subtitle>Welcome back!</v-list-item-subtitle>
                    </v-list-item-content>
                  </v-list-item>
                </v-list>
                <v-card-actions>
                  <v-spacer></v-spacer>
                  <v-btn depressed block @click="logout()">
                    Log Out
                    <v-icon right>mdi-exit-to-app</v-icon>
                  </v-btn>
                </v-card-actions>
              </v-card>
            </v-menu>
          </v-list-item>

          <v-btn
            text block
            class="mb-n2"
            @click.stop="mini = !mini" title="Collapse Sidebar"
            v-if="mini"
          >
            <v-icon>mdi-dock-left</v-icon>
          </v-btn>

          <v-container v-if="!mini">
            <v-row>
            <v-col class="px-2 py-0">
              <Settings></Settings>
            </v-col>
            <v-col class="px-0 py-0">
              <v-btn
                block depressed
                color="primary" class="blue darken-1"
                @click.stop="toggleDarkMode"
                :title="settings.darkMode ? 'Dark Mode: Off' : 'Dark Mode: On'"
              >
                <v-icon>{{ settings.darkMode ? 'mdi-lightbulb-off' : 'mdi-lightbulb-on' }}</v-icon>
              </v-btn>
            </v-col>
            <v-col class="px-2 py-0">
              <NotificationButton />
            </v-col>
            </v-row>
          </v-container>


          <v-list-item class="px-2" v-if="!mini">
            <v-menu offset-y v-if="isAuthenticated" :close-on-content-click="false">
              <template v-slot:activator="{ on }">
                <v-btn v-on="on"
                  block depressed
                  title="Select Project"
                  color="primary"
                  class="blue darken-1"
                >
                  Project: {{ selectedProject.name }}
                </v-btn>
              </template>
              <ProjectSelection v-on="on"> </ProjectSelection>
            </v-menu>
          </v-list-item>
        </div>

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
            <v-list-item dense
              v-for="([title, icon, to], i) in workflowsList"
              :key="i"
              :to="to"
              :value="to"
              v-if="!mini && isAuthenticated && _checkAuthR(policyData, to, currentUser)"
            >
              <v-list-item-action></v-list-item-action>
              <v-list-item-title>{{ title }}</v-list-item-title>
              <v-list-item-icon>
                <v-icon>{{ icon }}</v-icon>
              </v-list-item-icon>
            </v-list-item>
          </v-list-group>
          <v-list-group :prepend-icon="section.icon"
            v-if="isAuthenticated && checkAuthSection(policyData, section, currentUser)"
            v-for="(section, sectionKey) in externalWebpages" :key="section.id">
            <template v-slot:activator>
              <v-list-item-title>{{ section.label }}</v-list-item-title>
            </template>
            <v-list-item dense
              v-if="
                !mini &&
                section.subSections &&
                _checkAuthR(policyData, subSection.linkTo, currentUser)
              "
              v-for="(subSection, subSectionKey) in section.subSections"
              :key="subSection.id"
              :to="{
                name: 'ew-section-view',
                params: { ewSection: sectionKey, ewSubSection: subSectionKey },
              }">
              <v-list-item-action></v-list-item-action>
              <v-list-item-title v-text="subSection.label"></v-list-item-title>
            </v-list-item>
          </v-list-group>
          <!-- EXTENSIONS -->
          <v-list-item :to="'/extensions'"
            v-if="isAuthenticated && _checkAuthR(policyData, '/extensions', currentUser)">
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

        <!-- Sidebar bottom section -->
        <template v-slot:append>
          <v-container>
            <v-row class="pr-2 pb-2" v-if="!mini">
              <v-btn text href="/docs/faq_root.html" target="_blank" title="Help">
                <v-icon left size="24">mdi-help-circle</v-icon>
                Help
              </v-btn>
              <v-spacer></v-spacer>
              <v-btn icon @click="logout()" title="Log out">
                <v-icon>mdi-exit-to-app</v-icon>
              </v-btn>
            </v-row>
            <!-- <v-row class="px-2">
              &copy; DKFZ 2018 - DKFZ 2024
            </v-row> -->
            <v-row class="pa-2" v-else>
              <v-btn icon href="/docs/faq_root.html" target="_blank" title="Help">
                <v-icon >mdi-help-circle</v-icon>
              </v-btn>
            </v-row>
          </v-container>
        </template>

      </v-navigation-drawer>

      <v-main id="v-main-content">
        <router-view></router-view>
      </v-main>
    </v-app>
  </div>
</template>

<script lang="ts">
import Vue from "vue";
import VueCookies from 'vue-cookies';
Vue.use(VueCookies, { expires: '1d' })
import { mapGetters } from "vuex";
import httpClient from "@/common/httpClient.js";
import kaapanaApiService from "@/common/kaapanaApi.service";
import Settings from "@/components/Settings.vue";
import About from "@/components/About.vue";
import IdleTracker from "@/components/IdleTracker.vue";
import ProjectSelection from "@/components/ProjectSelection.vue";
import NotificationButton from "@/components/NotificationButton.vue";
import { settings as defaultSettings } from "@/static/defaultUIConfig";
import {
  CHECK_AVAILABLE_WEBSITES,
  LOGIN,
  LOGOUT,
  LOAD_COMMON_DATA,
  GET_POLICY_DATA,
  GET_SELECTED_PROJECT,
  CLEAR_SELECTED_PROJECT,
} from "@/store/actions.type";
import { checkAuthR } from "@/utils/utils.js";

export default Vue.extend({
  name: "App",
  components: { Settings, IdleTracker, ProjectSelection, About, NotificationButton },
  data: () => ({
    drawer: true,
    federatedBackendAvailable: false,
    settings: defaultSettings,
    failedToFetchTraefik: false,
    mini: false,
  }),
  computed: {
    ...mapGetters([
      "currentUser",
      "isAuthenticated",
      "externalWebpages",
      "workflowsList",
      "commonData",
      "policyData",
      "selectedProject",
      "availableProjects"
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
      this.storeSettingsItemInDb("darkMode");
    },
    toggleDarkMode() {
      this.changeMode(!this.settings["darkMode"]);
    },
    login() {
      this.$store.dispatch(LOGIN).then(() => this.$router.push({ name: "home" }));
    },
    logout() {
      this.$store.dispatch(LOGOUT);
    },
    onIdle() {
      this.$store.dispatch(LOGOUT).then(() => {
        this.$router.push({ name: "" });
      });
    },
    updateSettings() {
      this.settings = JSON.parse(localStorage["settings"]);
      this.$vuetify.theme.dark = this.settings["darkMode"];
    },
    settingsResponseToObject(response: any[]) {
      let converted: Object = {};
      response.forEach((item) => {
        converted[item.key as keyof Object] = item.value;
      });
      return converted;
    },
    getSettingsFromDb() {
      kaapanaApiService
        .kaapanaApiGet("/settings")
        .then((response: any) => {
          let settingsFromDb = this.settingsResponseToObject(response.data);
          const updatedSettings = Object.assign({}, defaultSettings, settingsFromDb);
          localStorage["settings"] = JSON.stringify(updatedSettings);
        })
        .catch((err) => {
          console.log(err);
          localStorage["settings"] = JSON.stringify(defaultSettings);
        });
    },
    storeSettingsItemInDb(item_name: string) {
      if (item_name in this.settings) {
        let item = {
          key: item_name,
          value: this.settings[item_name as keyof Object],
        };
        kaapanaApiService
          .kaapanaApiPut("/settings/item", item)
          .then((response) => {
            // console.log(response);
          })
          .catch((err) => {
            console.log(err);
          });
      }
    },
  },
  beforeCreate() {
    this.$store.dispatch(CHECK_AVAILABLE_WEBSITES);
    this.$store.dispatch(LOAD_COMMON_DATA);
    this.$store.dispatch(GET_POLICY_DATA);
    this.$store.dispatch(GET_SELECTED_PROJECT);
    if (!localStorage["settings"]) {
      localStorage["settings"] = JSON.stringify(defaultSettings);
    }
  },
  created() {
    this.$store.watch(
      () => this.$store.getters["isIdle"],
      (newValue, oldValue) => {
        if (newValue) {
          this.onIdle();
        }
      }
    );
    
    // Watch for changes in selectedProject and reload the page when it changes
    this.$store.watch(
      () => this.$store.getters.selectedProject,
      (newValue, oldValue) => {
        if (newValue !== oldValue) {
          const projectCookie = Vue.$cookies.get("Project");

          // If project cookie exists and the project doesn't match the cookie, set the cookies and reload
          if (newValue && projectCookie && projectCookie.name !== newValue.name ) {
            Vue.$cookies.set("Project", { name: newValue.name, id: newValue.id });
            location.reload(); // Reload the page
          } else if (this.failedToFetchTraefik) {
            // for some cases selectedProject as well as Project-Name cookie sets
            // after already made request to traefik and failed to Fetch Traefic.
            // In such cases, a reload is required after setting the Project-Name cookie.
            location.reload(); // Reload the page
          }
        }
      }
    );

    this.$store.watch(
      () => this.$store.getters.availableProjects,
      (newProjects: [any]) => {
        let found = false;
        const selectedProject = this.$store.getters.selectedProject;
        const currentUser = this.$store.getters.currentUser;

        // if the user not a kaapana_admin, check if the selected
        // project is listed in the available project for the user.
        // if not, clear the selected project from store and localstoraga,
        // reset the selected project by reloading
        if (!currentUser.groups.includes("kaapana_admin")) {
          for (const project of newProjects) {
            if (project.id == selectedProject.id) {
              found = true;
              break;
            }
          }

          if (!found) {
            this.$store.dispatch(CLEAR_SELECTED_PROJECT);
            location.reload(); // Reload the page
          }
        }
      }
    );

    this.getSettingsFromDb();
    this.updateSettings();
  },
  mounted() {
    httpClient
      .get("/kaapana-backend/get-traefik-routes")
      .then((response: { data: {} }) => {
        this.federatedBackendAvailable = kaapanaApiService.checkUrl(
          response.data,
          "/kaapana-backend"
        );
      })
      .catch((error: any) => {
        this.failedToFetchTraefik = true;
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

body {
  overflow: hidden;
}

.kaapana-iframe-container-side-navigation {
  height: 100vh;
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
