import { createApp } from 'vue'
import router from './router/router'
import vuetify from './plugins/vuetify'
import Notifications from '@kyvg/vue3-notification'
import Vueform from '@vueform/vueform'
import vueformConfig from './../vueform.config'
import App from './App.vue'


import 'vuetify/styles';
import '@mdi/font/css/materialdesignicons.css';
import 'roboto-fontface/css/roboto/roboto-fontface.css';
import './assets/styles.scss';

const app = createApp(App);
app.use(router);
app.use(Notifications);
app.use(vuetify);
app.use(Vueform, vueformConfig);
app.mount('#app');
