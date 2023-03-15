<template>
  <div id="app">
    <v-app id="inspire">
      <notifications position="bottom right" width="20%"/>
      <v-navigation-drawer clipped v-model="drawer" app class="ta-center">
        <v-list dense>
          <v-list-item :to="'/'">
            <v-list-item-action>
              <v-icon>mdi-home</v-icon>
            </v-list-item-action>
            <v-list-item-content>
              <v-list-item-title>Home</v-list-item-title>
            </v-list-item-content>
            <v-list-item-icon></v-list-item-icon>
          </v-list-item>
          <v-list-group :prepend-icon="section.icon"
                        v-if="isAuthenticated && section.roles.indexOf(currentUser.role) > -1"
                        v-for="(section, sectionKey) in externalWebpages" :key="section.id">
            <template v-slot:activator>
              <v-list-item-title>{{ section.label }}</v-list-item-title>
            </template>
            <v-list-item v-for="(subSection, subSectionKey) in section.subSections" :key="subSection.id"
                         :to="{ name: 'ew-section-view', params: { ewSection: sectionKey, ewSubSection: subSectionKey }}">
              <v-list-item-title v-text="subSection.label"></v-list-item-title>
            </v-list-item>
            <template v-if="section.label.toLowerCase() === 'monitoring'">
              <v-list-item v-for="provider of securityProviders" :key="provider.id" :to="'/security/' + provider.id">
                <v-list-item-title v-text="provider.name"></v-list-item-title>
              </v-list-item>
            </template>
          </v-list-group>
          <v-list-item :to="'/datasets'" v-if="isAuthenticated">
            <v-list-item-action>
              <v-icon>mdi-view-gallery-outline</v-icon>
            </v-list-item-action>
            <v-list-item-content>
              <v-list-item-title>Datasets</v-list-item-title>
            </v-list-item-content>
            <v-list-item-icon></v-list-item-icon>
          </v-list-item>
          <v-list-item :to="'/experiments'" v-if="isAuthenticated">
            <v-list-item-action>
              <v-icon>mdi-play-box</v-icon>
            </v-list-item-action>
            <v-list-item-content>
              <v-list-item-title>Experiments</v-list-item-title>
            </v-list-item-content>
            <v-list-item-icon></v-list-item-icon>
          </v-list-item>
          <!-- v-list-item :to="'/federated'" v-if="isAuthenticated && federatedBackendAvailable">
            <v-list-item-action>
              <v-icon>mdi-vector-triangle</v-icon>
            </v-list-item-action>
            <v-list-item-content>
              <v-list-item-title>Federated</v-list-item-title>
            </v-list-item-content>
            <v-list-item-icon></v-list-item-icon>
          </v-list-item -->
          <v-list-item :to="'/pending-applications'" v-if="isAuthenticated">
            <v-list-item-action>
              <v-icon>mdi-gamepad-variant</v-icon>
            </v-list-item-action>
            <v-list-item-content>
              <v-list-item-title>Pending applications</v-list-item-title>
            </v-list-item-content>
            <v-list-item-icon></v-list-item-icon>
          </v-list-item>
          <v-list-item :to="'/results-browser'" v-if="isAuthenticated && staticWebsiteAvailable">
            <v-list-item-action>
              <v-icon>mdi-file-tree</v-icon>
            </v-list-item-action>
            <v-list-item-content>
              <v-list-item-title>Results browser</v-list-item-title>
            </v-list-item-content>
            <v-list-item-icon></v-list-item-icon>
          </v-list-item>
          <v-list-group :prepend-icon="'mdi-security'" v-if="isAuthenticated && (!externalWebpages || !('monitoring' in externalWebpages) && securityProviders?.length > 0)">
            <template v-slot:activator>
              <v-list-item-title>Security</v-list-item-title>
            </template>
            <v-list-item v-for="provider of securityProviders" :key="provider.id" :to="'/security/' + provider.id">
              <v-list-item-title v-text="provider.name"></v-list-item-title>
            </v-list-item>
          </v-list-group>
          <v-list-item :to="'/extensions'" v-if="isAuthenticated">
            <v-list-item-action>
              <v-icon>mdi-apps</v-icon>
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
                <v-switch
                    label="Dark mode"
                    hide-details
                    v-model="darkMode"
                    @change="(v) => changeMode(v)"
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
import Vue from 'vue';
import request from '@/request';
import kaapanaApiService from '@/common/kaapanaApi.service'

import {mapGetters} from 'vuex';
import {LOGIN, LOGOUT, CHECK_AUTH} from '@/store/actions.type';
import {CHECK_AVAILABLE_WEBSITES, LOAD_COMMON_DATA, CHECK_SECURITY_PROVIDERS} from '@/store/actions.type';
import Settings from "@/components/Settings.vue";
import { DARK_MODE_ACTIVE, DARK_MODE_NOT_ACTIVE, QUERY_DARK_MODE } from './store/messages.type';

export default Vue.extend({
  name: 'App',
  components: {Settings},
  data: () => ({
    drawer: true,
    darkMode: 'darkMode' in localStorage ? JSON.parse(localStorage['darkMode']) : false,
    federatedBackendAvailable: false,
    staticWebsiteAvailable: false
  }),
  computed: {
    ...mapGetters(['currentUser', 'isAuthenticated', 'externalWebpages', 'commonData', 'securityProviders'])
  },
  methods: {
    changeMode(v: boolean) {
      this.darkMode = v
      localStorage['darkMode'] = JSON.stringify(v)
      this.$vuetify.theme.dark = v
      sendModeToIFrame(this.darkMode);
    },
    login() {
      this.$store
          .dispatch(LOGIN)
          .then(() => this.$router.push({name: 'home'}));
    },
    logout() {
      this.$store.dispatch(LOGOUT)
    },
    receiveMessage (event: MessageEvent) {
      console.log(event);

      // only process our own messages
      if (event.origin !== window.location.origin || !("message" in event.data)) {
        return;
      }
      if (event.data.message === QUERY_DARK_MODE) {
        sendModeToIFrame(this.darkMode);
      }
    }
  },
  beforeCreate() {
    this.$store.dispatch(CHECK_AVAILABLE_WEBSITES)
    this.$store.dispatch(LOAD_COMMON_DATA)
    this.$store.dispatch(CHECK_SECURITY_PROVIDERS)
  },
  mounted() {
    this.$vuetify.theme.dark = this.darkMode
    request.get('/traefik/api/http/routers').then((response: { data: {} }) => {
        this.federatedBackendAvailable = kaapanaApiService.checkUrl(response.data, '/kaapana-backend');
      }).catch((error: any) => {
        console.log('Something went wrong with traefik', error)
      });
    request.get('/traefik/api/http/routers').then((response: { data: {} }) => {
        this.staticWebsiteAvailable = kaapanaApiService.checkUrl(response.data, '/static-website-browser');
      }).catch((error: any) => {
        console.log('Something went wrong with traefik', error)
      });
  },
  created() {
    window.addEventListener("message", this.receiveMessage);
  },
  beforeDestroy() {
    window.removeEventListener("message", this.receiveMessage);
  },
  onIdle() {
    console.log('checking', this.$store.getters.isAuthenticated)
    this.$store
        .dispatch(CHECK_AUTH).then(() => {
      console.log('still online')
    }).catch((err: any) => {
      console.log('reloading')
      location.reload()
      // this.$router.push({ name: 'home' });
      // this.$store.dispatch(LOGOUT).then(() => {
      //   this.$router.push({ name: 'home' });
      // });
    })
  }
});

const sendModeToIFrame = (darkMode: boolean) => {
  const iframe_element = window.document.querySelector("iframe");
  if (!iframe_element) {
    return;
  }
  if (darkMode) {
    iframe_element.contentWindow?.postMessage({message: DARK_MODE_ACTIVE}, "*");
  } else {
    iframe_element.contentWindow?.postMessage({message: DARK_MODE_NOT_ACTIVE}, "*");
  }
};
</script>

<style lang='scss'>

$kaapana-blue: rgba(0, 71, 156, 0.95);
$kaapana-green: #ff7a20;

#app {
  font-family: 'Avenir', Helvetica, Arial, sans-serif;
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  //text-align: center;
  font-size: 14px;
  line-height: 1.42857143;
  color: #333;
}

.ta-center {
  text-align: center;
}

.router-container {
  //padding: 12px
}

// Example of colors
.kaapana-blue {
  color: $kaapana-blue
}

.kaapana-iframe-container {
  height: calc(100vh - 105px);
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

.kaapana-intro-header .kaapana-intro-image {
  padding-top: 10px;
  padding-bottom: 10px;
  //color: white;
  text-align: center;
  min-height: calc(100vh - 105px);
  //background: DeepSkyBlue;
  background-size: cover;
}

.kaapana-opacity-card {
  //background: rgba(255, 255, 255, 0.87) !important
}

.pa-0 {
  padding: 0;
}
</style>
