import Vue from 'vue';
import Vuetify from 'vuetify/lib';
import 'vuetify/dist/vuetify.min.css'
import '@mdi/font/css/materialdesignicons.css' // Ensure you are using css-loader
import Notifications from 'vue-notification'

import colors from 'vuetify/lib/util/colors'

Vue.use(Vuetify);
Vue.use(Notifications)

export default new Vuetify({
  theme: {
    themes: {
      light: {
        primary: '#005BA0',
        secondary: '#5A696E',
        accent: colors.shades.black,
        error: colors.red.darken2,
        jipgreen: '#ff7a20',
        jiplightgrey: '#eee',
      },
    },
  },
  icons: {
    iconfont: 'mdi',
  },
});