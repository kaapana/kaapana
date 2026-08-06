import 'vuetify/styles';
import { createVuetify } from 'vuetify';
import { aliases, mdi } from 'vuetify/iconsets/mdi';
import * as components from 'vuetify/components';
import * as directives from 'vuetify/directives';
import {
  kaapanaThemeLight,
  kaapanaThemeDark,
  KAAPANA_THEME_LIGHT,
  KAAPANA_THEME_DARK,
} from '@kaapana/base-ui';

// The workflows view adds a `navigation` brand color on top of the shared palette.
const light = { ...kaapanaThemeLight, colors: { ...kaapanaThemeLight.colors, navigation: '#FFFFFF' } };
const dark = { ...kaapanaThemeDark, colors: { ...kaapanaThemeDark.colors, navigation: '#363636' } };

export default createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: KAAPANA_THEME_LIGHT,
    themes: {
      [KAAPANA_THEME_LIGHT]: light,
      [KAAPANA_THEME_DARK]: dark,
    },
  },
  icons: {
    defaultSet: 'mdi',
    aliases,
    sets: { mdi },
  },
});
