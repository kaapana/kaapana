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
    background: '#FFFFFF',
    surface: '#F5F5F5',
    success: '#4CAF50',
    warning: '#FFC107',
    info: '#2196F3',
    'surface-variant': '#E0E0E0',
    'surface-bright': '#FFFFFF',
    'on-background': '#212121',
    'on-surface': '#212121',
    'on-primary': '#FFFFFF',
    'on-secondary': '#FFFFFF',
    'on-error': '#FFFFFF',
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
    surface: '#1E1E1E',
    success: '#4CAF50',
    warning: '#FFC107',
    info: '#2196F3',
    'surface-variant': '#2A2A2A',
    'surface-bright': '#333333',
    'on-background': '#FFFFFF',
    'on-surface': '#FFFFFF',
    'on-primary': '#FFFFFF',
    'on-secondary': '#FFFFFF',
    'on-error': '#FFFFFF',
  },
}

export default createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'kaapanaThemeDark',
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


