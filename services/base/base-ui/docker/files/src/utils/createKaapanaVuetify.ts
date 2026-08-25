import { createVuetify } from 'vuetify'
import type { VuetifyOptions } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi'
import { injectPlatformFonts } from './platformFonts'
import {
  KAAPANA_THEME_DARK,
  KAAPANA_THEME_LIGHT,
  kaapanaThemeDark,
  kaapanaThemeLight,
} from './vuetifyTheme'

// Builds the shared Vuetify configuration used by views and Storybook:
//
//     export default createKaapanaVuetify({ components, directives })
//
// Extra theme colors and icon aliases/sets extend the shared configuration.
// Other options retain Vuetify's normal replacement semantics.
export interface KaapanaVuetifyOptions extends VuetifyOptions {
  // Extra theme colours per theme name, for app-specific surfaces with no
  // semantic equivalent — portal-ui's `navigation` is the real case.
  extraThemeColors?: Record<string, Record<string, string>>
}

export function createKaapanaVuetify(options: KaapanaVuetifyOptions = {}) {
  // The platform typeface travels with the configuration, so a view cannot ship
  // the theme and forget the font.
  injectPlatformFonts()

  const { extraThemeColors, theme, defaults, icons, ...rest } = options
  // `theme` may legitimately be false (theming off); narrow before reading it.
  const themeOptions = typeof theme === 'object' && theme !== null ? theme : undefined

  const baseThemes = {
    [KAAPANA_THEME_LIGHT]: kaapanaThemeLight,
    [KAAPANA_THEME_DARK]: kaapanaThemeDark,
  }
  const themes = Object.fromEntries(
    Object.entries(baseThemes).map(([name, definition]) => [
      name,
      { ...definition, colors: { ...definition.colors, ...(extraThemeColors?.[name] ?? {}) } },
    ]),
  )
  const { aliases: customAliases, sets: customSets, ...iconOptions } = icons ?? {}

  return createVuetify({
    ...rest,
    theme:
      theme === false
        ? false
        : {
            defaultTheme: KAAPANA_THEME_LIGHT,
            ...themeOptions,
            themes: { ...themes, ...(themeOptions?.themes ?? {}) },
          },
    icons: {
      defaultSet: 'mdi',
      ...iconOptions,
      aliases: { ...aliases, ...customAliases },
      sets: { mdi, ...customSets },
    },
    defaults,
  })
}
