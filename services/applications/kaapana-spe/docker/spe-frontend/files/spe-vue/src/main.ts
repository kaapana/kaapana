// import './assets/main.css'

// import { createApp } from 'vue'
// import App from './App.vue'

// vuetify
// import 'vuetify/styles'


import App from "./App.vue";
// import "@mdi/font/css/materialdesignicons.css"; // Ensure you are using css-loader


// Composables
import { createApp } from "vue";

// Plugins
// import { registerPlugins } from "@/plugins";

// const app = createApp(App);

// registerPlugins(app);

import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

const vuetify = createVuetify({
    components,
    directives,
  })

// app.mount("#app");

// createApp(App).mount('#app')
createApp(App).use(vuetify).mount('#app')
