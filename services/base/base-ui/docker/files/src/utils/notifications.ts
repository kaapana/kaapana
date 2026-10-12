import { defineComponent, h, type App } from 'vue'
import NotificationsPlugin, { Notifications } from '@kyvg/vue3-notification'

export const KaapanaNotifications = defineComponent({
  name: 'KaapanaNotifications',
  inheritAttrs: false,
  setup(_, { attrs, slots }) {
    return () =>
      h(Notifications, { position: 'bottom right', width: '20%', duration: 5000, ...attrs }, slots)
  },
})

export const kaapanaNotifications = {
  install(app: App) {
    app.use(NotificationsPlugin, { componentName: 'BaseNotifications' })
    app.component('Notifications', KaapanaNotifications)
  },
}
