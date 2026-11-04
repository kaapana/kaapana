import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import vuetify from './plugins/vuetify'

import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import '@kaapana/base-ui/style.css'

createApp(App).use(createPinia()).use(vuetify).mount('#app')
