import 'vuetify/styles'
import { createKaapanaVuetify } from '@kaapana/base-ui'

// Theme, icon set and typeface come from the shared factory; do not re-declare
// them here.
export default createKaapanaVuetify({
  // The shared workflow form looks the same as in workflow-execution-ui. The
  // defaults also reach the fields that vjsf renders.
  defaults: {
    VTextField: { variant: 'outlined' },
    VTextarea: { variant: 'outlined' },
    VSelect: { variant: 'outlined' },
    VAutocomplete: { variant: 'outlined' },
    VCombobox: { variant: 'outlined' },
    VNumberInput: { variant: 'outlined' },
  },
})
