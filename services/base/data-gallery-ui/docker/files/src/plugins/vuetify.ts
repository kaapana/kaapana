import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi'
import {
  kaapanaThemeLight,
  kaapanaThemeDark,
  KAAPANA_THEME_LIGHT,
  KAAPANA_THEME_DARK,
} from '@kaapana/base-ui'

export default createVuetify({
  theme: {
    defaultTheme: KAAPANA_THEME_LIGHT,
    themes: {
      [KAAPANA_THEME_LIGHT]: kaapanaThemeLight,
      [KAAPANA_THEME_DARK]: kaapanaThemeDark,
    },
  },
  icons: {
    defaultSet: 'mdi',
    aliases,
    sets: { mdi },
  },
})
