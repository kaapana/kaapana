import { createKaapanaVuetify, KAAPANA_THEME_DARK, KAAPANA_THEME_LIGHT } from '@kaapana/base-ui'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

export default createKaapanaVuetify({
  components,
  directives,
  extraThemeColors: {
    [KAAPANA_THEME_LIGHT]: { navigation: '#FFFFFF' },
    [KAAPANA_THEME_DARK]: { navigation: '#363636' },
  },
})
