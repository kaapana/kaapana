import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Notifications from '@kyvg/vue3-notification'
import { kaapanaThemeDark, kaapanaThemeLight } from '@kaapana/base-ui'
import router from './router'
import vuetify from './plugins/vuetify'
import { resolveDarkMode, themeModeOf } from './stores/settings'
import App from './App.vue'

// createKaapanaVuetify adds the platform typeface, so no font is imported here.
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'

// Colours for the pages shown before Vuetify starts, when the theme's CSS
// variables do not exist yet. The stored theme choice is resolved like the
// settings store does it, so "System" asks the browser now.
function preMountColors(): Record<string, string> {
  let seed: Record<string, unknown> = {}
  try {
    seed = JSON.parse(localStorage['settings']) ?? {}
  } catch {
    // no settings persisted yet (or unparseable): the default choice applies
  }
  const darkMode = resolveDarkMode(themeModeOf(seed))
  return (darkMode ? kaapanaThemeDark : kaapanaThemeLight).colors as Record<string, string>
}

// The shell inside one of its own iframes means a view's URL fell through the
// gateway back to this SPA (broken/missing ingress route). Booting the full app
// would nest menu-in-menu — show a plain notice instead.
if (window.self !== window.top) {
  const { background, 'on-background': foreground, primary } = preMountColors()
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
  // The app mounts after the first navigation, which waits for the user, the
  // menu and the projects. Until then this spinner fills the page.
  const { background, primary } = preMountColors()
  document.getElementById('app')!.innerHTML = `
    <div role="status" aria-label="Loading the platform"
         style="display:flex;align-items:center;justify-content:center;height:100vh;background:${background}">
      <div style="width:48px;height:48px;border-radius:50%;border:4px solid ${primary}33;
                  border-top-color:${primary};animation:kaapana-boot-spin 1s linear infinite"></div>
    </div>
    <style>@keyframes kaapana-boot-spin { to { transform: rotate(360deg) } }</style>`

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
