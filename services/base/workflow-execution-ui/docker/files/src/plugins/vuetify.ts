import 'vuetify/styles';
import * as components from 'vuetify/components';
import * as directives from 'vuetify/directives';
import { createKaapanaVuetify } from '@kaapana/base-ui';

export default createKaapanaVuetify({
  components,
  directives,
  // Standardize on `outlined` for both template and vjsf-rendered fields.
  defaults: {
    VTextField: { variant: 'outlined' },
    VTextarea: { variant: 'outlined' },
    VSelect: { variant: 'outlined' },
    VAutocomplete: { variant: 'outlined' },
    VCombobox: { variant: 'outlined' },
    VNumberInput: { variant: 'outlined' },
  },
});
