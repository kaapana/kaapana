import 'vuetify/styles'
import { createKaapanaVuetify } from '@kaapana/base-ui'

// The shared factory carries the platform theme, the MDI icon set and the
// platform typeface (Roboto, injected at runtime) in one place, so this view
// cannot ship the theme and forget the font. Do not re-declare themes or icon
// sets here — see the design guidelines, "Visual language".
export default createKaapanaVuetify({
  defaults: {
    // The guidelines' 8px default corner radius ('lg' in Vuetify's scale),
    // set once here instead of at each call site.
    VCard: { rounded: 'lg' },
    VBtn: { rounded: 'lg' },
  },
})
