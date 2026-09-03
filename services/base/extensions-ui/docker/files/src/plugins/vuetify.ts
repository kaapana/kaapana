import 'vuetify/styles'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { createKaapanaVuetify } from '@kaapana/base-ui'

// The shared factory carries the platform theme, the MDI icon set and the
// platform typeface (Roboto, injected at runtime) in one place, so this view
// cannot ship the theme and forget the font. Do not re-declare themes or icon
// sets here — see the design guidelines, "Visual language".
export default createKaapanaVuetify({
  components,
  directives,
  // No component defaults for radius, spacing or elevation. The guidelines mark
  // "Spacing and shape" as *To be decided* and call the 4-vs-8px radius an
  // initial proposal, so committing to it here would give this one view corners
  // no other Kaapana view has — the divergence createKaapanaVuetify() exists to
  // prevent. When the decision lands it belongs in the shared factory.
})
