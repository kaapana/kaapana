import 'vuetify/styles';
import * as components from 'vuetify/components';
import * as directives from 'vuetify/directives';
import {
  createKaapanaVuetify,
  KAAPANA_THEME_LIGHT,
  KAAPANA_THEME_DARK,
} from '@kaapana/base-ui';

export default createKaapanaVuetify({
  components,
  directives,
  // The workflows view adds a `navigation` brand color on top of the shared palette.
  extraThemeColors: {
    [KAAPANA_THEME_LIGHT]: { navigation: '#FFFFFF' },
    [KAAPANA_THEME_DARK]: { navigation: '#363636' },
  },
});
