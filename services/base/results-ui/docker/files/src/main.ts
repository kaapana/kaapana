import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Notifications from '@kyvg/vue3-notification'
import App from './App.vue'
import router from './routes'
import vuetify from './plugins/vuetify'

import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(vuetify)
app.use(Notifications)
app.mount('#app')
