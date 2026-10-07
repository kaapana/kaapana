import 'vuetify/styles'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { createKaapanaVuetify } from '@kaapana/base-ui'

// Theme, icon set and typeface come from the shared factory; do not re-declare
// them here.
export default createKaapanaVuetify({
  components,
  directives,
})
