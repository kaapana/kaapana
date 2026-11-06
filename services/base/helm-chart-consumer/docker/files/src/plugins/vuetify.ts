import { createKaapanaVuetify, KAAPANA_THEME_DARK, KAAPANA_THEME_LIGHT } from '@kaapana/base-ui'

// The shared factory carries the Kaapana themes, the mdi icon set and the platform
// typeface. `navigation` is the shell's drawer colour, as in portal-ui.
export default createKaapanaVuetify({
  extraThemeColors: {
    [KAAPANA_THEME_LIGHT]: { navigation: '#FFFFFF' },
    [KAAPANA_THEME_DARK]: { navigation: '#363636' },
  },
})
