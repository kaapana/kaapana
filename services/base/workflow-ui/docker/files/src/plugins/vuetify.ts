import 'vuetify/styles';
import { createVuetify } from 'vuetify';
import { aliases, mdi } from 'vuetify/iconsets/mdi';
import colors from 'vuetify/util/colors';
import * as components from 'vuetify/components';
import * as directives from 'vuetify/directives';

const kaapanaThemeLight = {
  dark: false,
  colors: {
    primary: '#005BA0',
    secondary: '#5A696E',
    accent: colors.shades.black,
    error: colors.red.darken2,
    background: '#FFFFFF', // light mode background
  },
}

const kaapanaThemeDark = {
  dark: true,
  colors: {
    primary: '#005BA0',
    secondary: '#5A696E',
    accent: colors.shades.white,
    error: colors.red.darken2,
    background: '#121212',
  },
}

export default createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'kaapanaThemeDark', // start in dark mode
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


