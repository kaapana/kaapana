// Toast colours from the platform theme instead of @kyvg/vue3-notification's own
// fixed palette, which ignores dark mode and puts white text on light orange and
// green. Each type takes its theme role and that role's contrasting `on-` colour,
// so the pair follows the shell's theme. The library styles `warn`; `warning`,
// Vuetify's spelling, is styled too so neither spelling falls back to blue.
//
// Scoped to `.v-application`, where Vuetify defines the theme variables; that
// also outranks the library's own rules whatever order the sheets load in.
const CSS = `
.v-application .vue-notification {
  background: rgb(var(--v-theme-info));
  color: rgb(var(--v-theme-on-info));
  border-left-color: rgba(0, 0, 0, 0.2);
}
.v-application .vue-notification.success {
  background: rgb(var(--v-theme-success));
  color: rgb(var(--v-theme-on-success));
}
.v-application .vue-notification.warn,
.v-application .vue-notification.warning {
  background: rgb(var(--v-theme-warning));
  color: rgb(var(--v-theme-on-warning));
}
.v-application .vue-notification.error {
  background: rgb(var(--v-theme-error));
  color: rgb(var(--v-theme-on-error));
}
`

const STYLE_ID = 'kaapana-notification-styles'

export function injectNotificationStyles(): void {
  if (typeof document === 'undefined') return
  if (document.getElementById(STYLE_ID)) return
  const style = document.createElement('style')
  style.id = STYLE_ID
  style.textContent = CSS
  document.head.appendChild(style)
}
