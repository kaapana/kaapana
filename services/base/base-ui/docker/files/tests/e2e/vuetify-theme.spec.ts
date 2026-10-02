import { expect, test } from '@playwright/test'
import type { ThemeDefinition } from 'vuetify'
import { contrastingColor, kaapanaThemeDark, kaapanaThemeLight } from '../../src/utils/vuetifyTheme'

// Checked by `npm run type-check`: an empty list leaves nothing to pick.
// @ts-expect-error
void (() => contrastingColor('#FFFFFF', []))

test.describe('contrastingColor', () => {
  test('picks black on a light background and white on a dark one', () => {
    expect(contrastingColor('#FFFFFF')).toBe('#000000')
    expect(contrastingColor('#EF6C00')).toBe('#000000')
    expect(contrastingColor('#2E7D32')).toBe('#FFFFFF')
    expect(contrastingColor('#000000')).toBe('#FFFFFF')
  })

  test('picks the choice with the highest contrast', () => {
    // On white: #005BA0 6.99 : 1, #777777 4.48 : 1, #FFFF00 1.07 : 1.
    expect(contrastingColor('#FFFFFF', ['#FFFF00', '#005BA0', '#777777'])).toBe('#005BA0')
  })

  test('a tie goes to the earlier choice, returned as passed', () => {
    expect(contrastingColor('#000000', ['#ffffff', '#FFFFFF'])).toBe('#ffffff')
    expect(contrastingColor('#000000', ['#FFFFFF', '#ffffff'])).toBe('#FFFFFF')
  })
})

function onColours(theme: ThemeDefinition) {
  return Object.fromEntries(Object.entries(theme.colors ?? {}).filter(([key]) => key.startsWith('on-')))
}

// The AA picks: e.g. light warning takes black and light success white, where
// Vuetify's own APCA derivation would take white for both.
test('the themes keep their on-* colours', () => {
  expect(onColours(kaapanaThemeLight)).toEqual({
    'on-primary': '#FFFFFF',
    'on-secondary': '#FFFFFF',
    'on-background': '#000000',
    'on-surface': '#000000',
    'on-surface-light': '#000000',
    'on-surface-bright': '#000000',
    'on-surface-variant': '#FFFFFF',
    'on-error': '#FFFFFF',
    'on-warning': '#000000',
    'on-success': '#FFFFFF',
    'on-info': '#FFFFFF',
    'on-accent': '#FFFFFF',
  })
  expect(onColours(kaapanaThemeDark)).toEqual({
    'on-primary': '#000000',
    'on-secondary': '#FFFFFF',
    'on-background': '#FFFFFF',
    'on-surface': '#FFFFFF',
    'on-surface-light': '#FFFFFF',
    'on-surface-bright': '#FFFFFF',
    'on-surface-variant': '#000000',
    'on-error': '#000000',
    'on-warning': '#000000',
    'on-success': '#000000',
    'on-info': '#000000',
    'on-accent': '#000000',
  })
})
