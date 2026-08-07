import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Notifications from '@kyvg/vue3-notification'
import router from './router'
import vuetify from './plugins/vuetify'
import App from './App.vue'

import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import 'roboto-fontface/css/roboto/roboto-fontface.css'

// The shell inside one of its own iframes means a view's URL fell through the
// gateway back to this SPA (broken/missing ingress route). Booting the full app
// would nest menu-in-menu — show a plain notice instead.
if (window.self !== window.top) {
  // Vuetify has not run yet, so --v-theme-* does not exist: read the same
  // localStorage["settings"] the shell persists and inline the theme's own
  // background/primary, defaulting to dark like defaultUIConfig does.
  let darkMode = true
  try {
    darkMode = JSON.parse(localStorage['settings']).darkMode ?? true
  } catch {
    // no settings persisted yet (or unparseable): keep the default
  }
  const background = darkMode ? '#121212' : '#FFFFFF'
  const foreground = darkMode ? '#FFFFFF' : '#000000'
  const primary = darkMode ? '#42A5F5' : '#005BA0'
  document.getElementById('app')!.innerHTML = `
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
                height:100vh;gap:12px;font-family:Roboto,sans-serif;text-align:center;padding:16px;
                background:${background};color:${foreground}">
      <h2 style="font-weight:500">This view could not be loaded</h2>
      <p>The requested page redirected back to the platform itself — the service may be
         missing or its link is broken.</p>
      <a href="/" target="_top" style="color:${primary}">Go to the homepage</a>
    </div>`
} else {
  const app = createApp(App)
  app.use(createPinia())
  app.use(router)
  app.use(vuetify)
  app.use(Notifications)
  // Mount only after the initial navigation settles: the guard's /project
  // redirect must be committed before components mount, so the pathname-based
  // http interceptor scopes the shell's first project calls deterministically.
  router.isReady().then(() => app.mount('#app'))
}
