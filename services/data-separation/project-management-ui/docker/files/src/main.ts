import { registerPlugins } from '@/plugins'
import App from './App.vue'
import { createApp } from 'vue'
import { createPinia } from 'pinia'

import '@kaapana/base-ui/style.css'

const app = createApp(App)

registerPlugins(app)

app.use(createPinia());

app.mount('#app')
