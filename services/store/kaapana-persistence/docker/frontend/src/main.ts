/**
 * main.ts
 *
 * Bootstraps Vuetify and other plugins then mounts the App`
 */

// Components
import App from "./App.vue";

// Composables
import { createApp } from "vue";

// Plugins
import { registerPlugins } from "@/plugins";

import axios from "axios";
if (process.env.VUE_APP_API_ENDPOINT) {
  axios.defaults.baseURL = process.env.VUE_APP_API_ENDPOINT;
}

const app = createApp(App);

registerPlugins(app);

app.mount("#app");
