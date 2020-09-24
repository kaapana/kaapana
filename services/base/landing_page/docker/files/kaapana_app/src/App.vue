<template lang="pug">
#app
  v-app#inspire
    v-navigation-drawer(clipped v-model="drawer" app)
      v-list(dense)
        v-list-item(:to="'/'")
          v-list-item-action
            v-icon mdi-home
          v-list-item-content
            v-list-item-title Home
          v-list-item-icon
        v-list-group(:prepend-icon="section.icon" v-if="isAuthenticated && section.roles.indexOf(currentUser.role) > -1" v-for="(section, sectionKey) in externalWebpages" :key="section.id")
          template(v-slot:activator)
            v-list-item-title {{section.label}}
          v-list-item(v-for="(subSection, subSectionKey) in section.subSections" :key="subSection.id" :to="{ name: 'ew-section-view', params: { ewSection: sectionKey, ewSubSection: subSectionKey }}")
            v-list-item-title(v-text="subSection.label")
        v-list-item(:to="'/application-links'" v-if="isAuthenticated")
          v-list-item-action
            v-icon mdi-gamepad-variant
          v-list-item-content
            v-list-item-title Pending applications
          v-list-item-icon
        v-list-item(:to="'/data-upload'" v-if="isAuthenticated")
          v-list-item-action
            v-icon mdi-cloud-upload
          v-list-item-content
            v-list-item-title Data upload
          v-list-item-icon
    v-app-bar(color="primary" dark dense clipped-left app)
      v-app-bar-nav-icon(@click.stop="drawer = !drawer")
      v-toolbar-title {{ commonData.name }}
      v-spacer
      v-menu(v-if="isAuthenticated" :close-on-content-click='false', :nudge-width='200', offset-x)
        template(v-slot:activator='{ on }')
          v-btn(v-on='on', icon)
            v-icon mdi-account-circle
        v-card
          v-list
            v-list-item
              v-list-item-content
                v-list-item-title {{currentUser.username}}
                  p Welcome back!
          v-card-actions
            v-spacer
            v-btn(icon @click="logout()")
              v-icon mdi-exit-to-app
    v-content#v-main-content
      v-container.router-container(fluid fill-height)
        v-layout(justify-center align-start)
          v-flex(text-xs-center)
            router-view
    v-footer(color="primary" app inset)
      span.white--text &copy; DKFZ 2018 - DKFZ 2020: Version {{commonData.version}}
</template>


<script lang="ts">
import Vue from 'vue';
import storage from 'local-storage-fallback'
import request from '@/request';

import { mapGetters } from 'vuex';
import { LOGIN, LOGOUT, CHECK_AUTH } from '@/store/actions.type';
import { CHECK_AVAILABLE_WEBISTES, LOAD_COMMON_DATA, LOAD_LAUNCH_APPLICATION_DATA} from '@/store/actions.type';

export default Vue.extend({
  name: 'App',
  data: () => ({
    drawer: true,
  }),
  computed: {
    ...mapGetters(['currentUser', 'isAuthenticated', 'externalWebpages', 'commonData']),
  },
  mounted() {
    this.minioCall()
  },
  methods: {
    login() {
      this.$store
          .dispatch(LOGIN)
          .then(() => this.$router.push({ name: 'home' }));
    },
    logout() {
      this.$store.dispatch(LOGOUT)
    },
    minioCall() {
         request.get('/flow/kaapana/api/getaccesstoken').then(response => {
            console.log(response)
            let payload = {"id":1,"jsonrpc":"2.0","params":{"token": response.data["xAuthToken"]},"method":"Web.LoginSTS"}
            request.post('/minio/webrpc', payload).then(response => {
                console.log(response)
                storage.setItem('token', `${response.data.result["token"]}`)
            }).catch(error => {
              console.log('Could not generate the minio token...', error)
            })
        }).catch(error => {
          console.log('Could not load the access-token', error)
        })
    }
  },
  beforeCreate () {
    this.$store.dispatch(CHECK_AVAILABLE_WEBISTES)
    this.$store.dispatch(LOAD_COMMON_DATA)
    this.$store.dispatch(LOAD_LAUNCH_APPLICATION_DATA)
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
</script>

<style lang='scss'>

$kaapana-blue: rgba(0, 71, 156, 0.95);
$kaapana-green: #ff7a20;

#app {
  font-family: 'Avenir', Helvetica, Arial, sans-serif;
  font-family: "Helvetica Neue",Helvetica,Arial,sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  font-size: 14px;
  line-height: 1.42857143;
  color: #333;
}

.router-container {
  padding: 12px
}
// Example of colors
.kaapana-blue {
  color: $kaapana-blue
}

.kaapana-iframe-container{
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
  padding:10px;
}
.kaapana-intro-header{
  position: relative;
} 
.kaapana-intro-header .kaapana-intro-image{
  padding-top: 10px;
  padding-bottom: 10px; 
  color: white;
  text-align: center;
  min-height: calc(100vh - 105px);
  background: url(assets/img/bg2.jpg) no-repeat center center;
  background-size: cover;
}

.kaapana-opacity-card{
  background: rgba(255, 255, 255, 0.87) !important
}

</style>
