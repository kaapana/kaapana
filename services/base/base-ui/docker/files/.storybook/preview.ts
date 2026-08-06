import { setup } from '@storybook/vue3-vite'
import { createVuetify } from 'vuetify'
import { createPinia } from 'pinia'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'

// The consuming views all run inside a Vuetify + Pinia app; mirror that here.
setup((app) => {
  app.use(createVuetify())
  app.use(createPinia())
})
