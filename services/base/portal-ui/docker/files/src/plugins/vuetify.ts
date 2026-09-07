import 'vuetify/styles';
import { createVuetify } from 'vuetify';
import { aliases, mdi } from 'vuetify/iconsets/mdi';
import colors from 'vuetify/util/colors';
import * as components from 'vuetify/components';
import * as directives from 'vuetify/directives';

// Stock light/dark palettes with only the brand colors overridden;
// `navigation` is the drawer background (white / #363636).
const kaapanaThemeLight = {
  dark: false,
  colors: {
    primary: '#005BA0',
    secondary: '#5A696E',
    accent: colors.shades.black,
    error: colors.red.darken2,
    navigation: '#FFFFFF',
  },
}

const kaapanaThemeDark = {
  dark: true,
  colors: {
    // Brighter than the light-theme brand blue: #005BA0 is too dim on dark
    // surfaces to tell the active nav entry apart.
    primary: '#42A5F5',
    secondary: '#5A696E',
    accent: colors.shades.white,
    error: colors.red.darken2,
    background: '#121212',
    surface: '#1E1E1E',
    navigation: '#363636',
  },
}

export default createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'kaapanaThemeLight',
    themes: {
      kaapanaThemeLight,
      kaapanaThemeDark,
    },
  },
  icons: {
    defaultSet: 'mdi',
    aliases,
    sets: { mdi },
  },
})


