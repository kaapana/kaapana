import { describe, it, expect } from 'vitest'
import { KAAPANA_THEME_DARK, KAAPANA_THEME_LIGHT } from '@kaapana/base-ui'
import vuetify from '@/plugins/vuetify'

// The shell used to carry a copy of the theme that drifted from the views'.
// These guards fail if the plugin stops going through the shared factory.
describe('vuetify plugin', () => {
  const themes = vuetify.theme.themes.value

  it('offers the two shared themes under their shared names', () => {
    // Vuetify always adds its stock `light` and `dark` next to them.
    expect(themes[KAAPANA_THEME_LIGHT]!.dark).toBe(false)
    expect(themes[KAAPANA_THEME_DARK]!.dark).toBe(true)
    expect(vuetify.theme.global.name.value).toBe(KAAPANA_THEME_LIGHT)
  })

  it('keeps the drawer colour on top of the shared palette', () => {
    expect(themes[KAAPANA_THEME_LIGHT]!.colors.navigation).toBe('#FFFFFF')
    expect(themes[KAAPANA_THEME_DARK]!.colors.navigation).toBe('#363636')
    // Tokens the shell's own copy of the theme was missing.
    for (const name of [KAAPANA_THEME_LIGHT, KAAPANA_THEME_DARK]) {
      for (const token of ['background', 'surface', 'error', 'warning', 'success', 'info']) {
        expect(themes[name]!.colors[token], `${name}.${token}`).toMatch(/^#[0-9A-F]{6}$/i)
      }
    }
  })

  it('injects the platform typeface with the configuration', () => {
    const style = document.getElementById('kaapana-platform-fonts')
    expect(style?.textContent).toMatch(/font-family:\s*['"]?Roboto/)
  })
})
