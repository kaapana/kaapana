import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { computed, defineComponent, h } from 'vue'
import { useTheme } from 'vuetify'
import { VCard, VCardText, VCardTitle, VCol, VRow, VSheet } from 'vuetify/components'
import { themeContrastRatio } from '../utils/vuetifyTheme'
import { note } from './storyNote'

// Reads the live theme rather than a copied table, so this page cannot drift
// from the configuration applications receive. Switch themes in the toolbar.
const ColorsAndThemes = defineComponent({
  name: 'ColorsAndThemes',
  setup() {
    const theme = useTheme()
    // Include every configured role. The `on-*` roles are rendered as each
    // background's foreground and therefore do not need separate swatches.
    const roles = computed(() => {
      const colours = theme.current.value.colors as Record<string, string | undefined>
      return Object.keys(colours)
        .filter((k) => !k.startsWith('on-') && !k.includes('-darken') && !k.includes('-lighten'))
        .sort()
        .map((name) => {
          const value = colours[name]
          const foreground = colours[`on-${name}`]
          return {
            name,
            value,
            ratio: value && foreground ? themeContrastRatio(value, foreground) : undefined,
          }
        })
    })

    return () =>
      h('div', [
        note(
          'Use semantic theme roles instead of local color values. Each swatch shows the active ' +
            'theme value and its on-color contrast ratio; WCAG AA requires 4.5:1 for body text. ' +
            'Background and surface remain distinct in both themes.',
        ),
        h(VCard, null, {
          default: () => [
            h(VCardTitle, null, { default: () => 'Surface on background' }),
            h(VCardText, null, {
              default: () =>
                h(VRow, null, {
                default: () =>
                  roles.value.map((role) =>
                    h(VCol, { cols: 6, sm: 4, md: 3, key: role.name }, {
                      default: () =>
                        h(VSheet, { color: role.name, class: 'pa-3', rounded: true, border: true }, {
                          default: () => [
                            h('div', { class: 'text-subtitle-2' }, role.name),
                            h('div', { class: 'text-caption' }, role.value ?? '—'),
                            h(
                              'div',
                              { class: 'text-caption' },
                              role.ratio
                                ? `on-${role.name} · ${role.ratio.toFixed(2)}:1`
                                : 'no on- pair configured',
                            ),
                          ],
                        }),
                    }),
                  ),
                }),
            }),
          ],
        }),
      ])
  },
})

const meta: Meta<typeof ColorsAndThemes> = {
  title: 'Guidelines / Foundations / Colors & Themes',
  component: ColorsAndThemes,
}

export default meta
type Story = StoryObj<typeof ColorsAndThemes>

export const Default: Story = {}
