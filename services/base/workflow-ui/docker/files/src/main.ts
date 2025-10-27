import { createApp } from 'vue'
import router from './router/router'
import vuetify from './plugins/vuetify'
import App from './App.vue'


import 'vuetify/styles';
import '@mdi/font/css/materialdesignicons.css';
import 'roboto-fontface/css/roboto/roboto-fontface.css';
import './assets/styles.scss';

const app = createApp(App);
app.use(router);
app.use(vuetify);
app.mount('#app');
