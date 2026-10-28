import { registerPlugins } from '@/plugins'
import App from './App.vue'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Notifications from '@kyvg/vue3-notification'

import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import '@kaapana/base-ui/style.css'

const app = createApp(App)

registerPlugins(app)

app.use(createPinia())
app.use(Notifications)

app.mount('#app')
