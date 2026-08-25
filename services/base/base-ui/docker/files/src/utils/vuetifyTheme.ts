import type { ThemeDefinition } from 'vuetify'

// Shared Kaapana theme. The views embed under the portal-ui shell, whose
// dark-mode toggle switches between these two themes by name — hence the
// exported name constants (a lookup mismatch silently disables dark mode).
//
// The semantic roles below are the ones the design guidelines define. Values are
// kept as literals rather than palette lookups so the table here can be read
// against the guideline's colour table directly.
export const KAAPANA_THEME_LIGHT = 'kaapanaThemeLight'
export const KAAPANA_THEME_DARK = 'kaapanaThemeDark'

// Black or white per background, whichever wins on WCAG 2.1 contrast ratio.
//
// Vuetify derives `on-*` itself when we leave it out, but it measures APCA and
// prefers white: against this palette that picks white on warning and success,
// which fails the AA ratio the guidelines commit to. Deriving here keeps the
// pairs structural — nobody maintains them by hand — while meeting that target.
function relativeLuminance(hex: string): number {
  const channel = (v: number) => {
    const c = v / 255
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  }
  const h = hex.replace('#', '')
  const [r, g, b] = [0, 2, 4].map((i) => channel(parseInt(h.slice(i, i + 2), 16)))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

// Exported for the colour reference story, which states the measured ratio next
// to each swatch so a failing pair is visible rather than merely present.
export function themeContrastRatio(background: string, foreground: string): number {
  const [backgroundLuminance, foregroundLuminance] = [
    relativeLuminance(background),
    relativeLuminance(foreground),
  ]
  return (
    (Math.max(backgroundLuminance, foregroundLuminance) + 0.05) /
    (Math.min(backgroundLuminance, foregroundLuminance) + 0.05)
  )
}

function withForegrounds(theme: ThemeDefinition): ThemeDefinition {
  const colours = { ...theme.colors } as Record<string, string>
  for (const [key, value] of Object.entries(theme.colors ?? {})) {
    if (key.startsWith('on-')) continue
    colours[`on-${key}`] =
      themeContrastRatio(value as string, '#FFFFFF') >
      themeContrastRatio(value as string, '#000000')
        ? '#FFFFFF'
        : '#000000'
  }
  return { ...theme, colors: colours }
}

export const kaapanaThemeLight: ThemeDefinition = withForegrounds({
  dark: false,
  colors: {
    primary: '#005BA0',
    secondary: '#5A696E',
    background: '#EEEEEE',
    surface: '#FFFFFF',
    // Vuetify's surface roles, kept to Vuetify's own semantics rather than
    // renamed. `surface-light` is the subtle secondary surface — VToolbar, flat
    // VAlert, select masks, 13 styles in all. `surface-variant` is the *inverted*
    // contrast surface: dark in the light theme, light in the dark one, used by
    // tooltips, badges, chips, snackbars, switch tracks and sliders (18 styles).
    // Both are inherited from Vuetify's defaults if left unset, which is how a
    // pale lavender switch thumb ended up in the dark theme.
    'surface-light': '#F5F5F5',
    'surface-bright': '#FFFFFF',
    'surface-variant': '#424242',
    error: '#C62828',
    warning: '#EF6C00',
    success: '#2E7D32',
    info: '#0277BD',
    accent: '#000000',
  },
})

export const kaapanaThemeDark: ThemeDefinition = withForegrounds({
  dark: true,
  colors: {
    // Brighter than the light-theme brand blue: #005BA0 is too dim on dark
    // surfaces to tell the active nav entry apart.
    primary: '#42A5F5',
    secondary: '#5A696E',
    background: '#121212',
    surface: '#1E1E1E',
    'surface-light': '#383838',
    'surface-bright': '#424242',
    // Inverted, as in the light theme — a light grey so tooltips and badges stay
    // legible against dark content.
    'surface-variant': '#C8C8C8',
    error: '#EF5350',
    warning: '#FFA726',
    success: '#66BB6A',
    info: '#29B6F6',
    accent: '#FFFFFF',
  },
})
