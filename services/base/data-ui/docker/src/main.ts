import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import { vuetify } from './plugins/vuetify'
import { router } from './router'
import './styles/main.scss'

const app = createApp(App)
app.use(createPinia())
app.use(vuetify)
app.use(router)
app.mount('#app')
