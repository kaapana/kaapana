// The platform typeface, carried by the library instead of by every view.
//
// Vuetify's stylesheet asks for `"Roboto", sans-serif` in 81 separate rule blocks
// and exposes no CSS custom property for the family, so a view that does not ship
// the face renders in whatever the client OS substitutes for `sans-serif` — Arial
// on Windows, DejaVu on Linux. Nothing errors; the platform just looks different
// per machine. Views used to be expected to remember an import for this, and the
// nine new ones did not.
//
// `?inline` gives us the stylesheet as a string rather than as an emitted file.
// That matters: Vite's library mode inlines font assets as base64 data URIs
// regardless of `assetsInlineLimit`, so these three sheets carry their own fonts
// and have no relative URLs left to resolve. They can therefore be injected at
// runtime, which is what removes the import from the consuming view entirely.
//
// The cost is ~174 kB of data URIs inside the bundle. In exchange there is no
// font request at all, and no view can forget the typeface. Only the three weights
// Vuetify actually asks for are included: 400 appears 53 times in its stylesheet,
// 500 thirty-five times, 300 fifteen. The remaining weights it names once each
// (100/600/700/900) are left to the browser to synthesise.
import roboto300 from '@fontsource/roboto/latin-300.css?inline'
import roboto400 from '@fontsource/roboto/latin-400.css?inline'
import roboto500 from '@fontsource/roboto/latin-500.css?inline'

const STYLE_ID = 'kaapana-platform-fonts'

/**
 * Adds the platform typeface to the document, once.
 *
 * Called by `createKaapanaVuetify()`, so a view that uses the shared Vuetify
 * configuration gets the face without doing anything. Safe to call repeatedly and
 * safe outside a browser.
 */
export function injectPlatformFonts(): void {
  if (typeof document === 'undefined') return
  if (document.getElementById(STYLE_ID)) return
  const style = document.createElement('style')
  style.id = STYLE_ID
  style.textContent = [roboto300, roboto400, roboto500].join('\n')
  document.head.appendChild(style)
}
