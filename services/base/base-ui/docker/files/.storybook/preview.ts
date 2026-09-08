import type { Preview } from '@storybook/vue3-vite'
import { setup } from '@storybook/vue3-vite'
import { h } from 'vue'
import { VApp } from 'vuetify/components'
import { createPinia } from 'pinia'
import NotificationsPlugin, { Notifications } from '@kyvg/vue3-notification'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
// createKaapanaVuetify() injects the platform typeface, just as it does for a view.
import { createKaapanaVuetify } from '../src/utils/createKaapanaVuetify'
import { KAAPANA_THEME_DARK, KAAPANA_THEME_LIGHT } from '../src/utils/vuetifyTheme'

const vuetify = createKaapanaVuetify()

setup((app) => {
  app.use(vuetify)
  app.use(createPinia())
  // The views report transient outcomes through this library — kaapanaApiService
  // already does — so the reference has to use it rather than a stand-in.
  app.use(NotificationsPlugin)
})

const preview: Preview = {
  parameters: {
    // The story owns the canvas: Storybook's default layout frames it in white,
    // which hides the theme's own page background — the one thing the colour
    // reference exists to show. Padding comes from the decorator instead.
    layout: 'fullscreen',
    // Vuetify's themes paint the canvas; Storybook's own backgrounds would sit
    // in front of them.
    backgrounds: { disable: true },
    options: {
      storySort: {
        order: [
          'Guidelines',
          ['Foundations', 'Actions', 'Forms', 'Dialogs', 'Patterns', 'Feedback', 'Data', 'Layout'],
          'Library',
          '*',
        ],
      },
    },
  },
  globalTypes: {
    theme: {
      description: 'Kaapana theme',
      defaultValue: KAAPANA_THEME_LIGHT,
      toolbar: {
        title: 'Theme',
        icon: 'paintbrush',
        items: [
          { value: KAAPANA_THEME_LIGHT, title: 'Light' },
          { value: KAAPANA_THEME_DARK, title: 'Dark' },
        ],
        dynamicTitle: true,
      },
    },
  },
  decorators: [
    // Same switch the shell performs through useShellSettings, driven from the
    // toolbar: "does this hold up in both themes" becomes a two-click check.
    (story, context) => {
      vuetify.theme.global.name.value = context.globals.theme ?? KAAPANA_THEME_LIGHT
      return () =>
        h(VApp, null, {
          default: () => [
            h('div', { class: 'pa-6' }, [h(story())]),
            h(Notifications, { position: 'bottom right', width: '20%', duration: 5000 }),
          ],
        })
    },
  ],
}

export default preview
