import colors from 'vuetify/util/colors'
import type { ThemeDefinition } from 'vuetify'

// Brand colors on the stock light/dark palettes. The shell's dark-mode toggle
// switches themes by these exported names — a mismatch silently disables dark mode.
export const KAAPANA_THEME_LIGHT = 'kaapanaThemeLight'
export const KAAPANA_THEME_DARK = 'kaapanaThemeDark'

export const kaapanaThemeLight: ThemeDefinition = {
  dark: false,
  colors: {
    primary: '#005BA0',
    secondary: '#5A696E',
    accent: colors.shades.black,
    error: colors.red.darken2,
  },
}

export const kaapanaThemeDark: ThemeDefinition = {
  dark: true,
  colors: {
    primary: '#42A5F5',
    secondary: '#5A696E',
    accent: colors.shades.white,
    error: colors.red.darken2,
    background: '#121212',
    surface: '#1E1E1E',
  },
}
