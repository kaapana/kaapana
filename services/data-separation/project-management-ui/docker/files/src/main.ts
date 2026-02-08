/**
 * main.ts
 *
 * Bootstraps Vuetify and other plugins then mounts the App`
 */

// Plugins
import { registerPlugins } from '@/plugins'

// Components
import App from './App.vue'

// Composables
import { createApp } from 'vue'

import { createPinia } from "pinia";

import { useCookies } from "vue3-cookies";


const app = createApp(App)

registerPlugins(app)

app.use(createPinia());
app.use(useCookies);

app.mount('#app')
