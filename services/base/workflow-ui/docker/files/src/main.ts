import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { kaapanaNotifications } from '@kaapana/base-ui'
import router from './router/router'
import vuetify from './plugins/vuetify'
import App from './App.vue'

import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import '@kaapana/base-ui/style.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(vuetify)
app.use(kaapanaNotifications)
app.mount('#app')
