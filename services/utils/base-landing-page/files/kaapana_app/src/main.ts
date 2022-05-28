import 'babel-polyfill'
import Vue from 'vue'
import App from './App.vue'
import router from './routes'
import store from './store'
import vuetify from './plugins/vuetify'
import IdleVue from 'idle-vue'

const eventsHub = new Vue()

Vue.use(IdleVue, {
  eventEmitter: eventsHub,
  // idleTime: 240000, //every 6 minute
  idleTime: 1900000, //after ~30 minute
  //idleTime: 190000, //every ~30 minute
  events: ['keydown', 'mousedown', 'touchstart']
})

Vue.config.productionTip = true;

new Vue({
  router,
  store,
  vuetify,
  render: (h) => h(App),
}).$mount('#app');
