import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { defineComponent, h } from 'vue'
import { VCard, VCardText, VCardTitle, VCol, VIcon, VRow, VSheet } from 'vuetify/components'
import { kaapanaIcons } from '../utils/icons'
import { note } from './storyNote'

// Reads the map rather than listing icons, so the page cannot drift from what
// the platform exports — the same arrangement the colour page uses for tokens.
const actions = Object.entries(kaapanaIcons).sort(([a], [b]) => a.localeCompare(b))

const Icons = defineComponent({
  name: 'Icons',
  setup() {
    return () =>
      h('div', [
        note(
          'Use one recognizable symbol for each action. Reference the semantic name from the shared ' +
            'icon map instead of writing an mdi name at the call site. Icon-only controls still need ' +
            'an accessible name.',
        ),
        h(VCard, null, {
          default: () => [
            h(VCardTitle, null, { default: () => `${actions.length} named actions` }),
            h(VCardText, null, {
              default: () =>
                h(VRow, null, {
                  default: () =>
                    actions.map(([action, icon]) =>
                      h(VCol, { cols: 6, sm: 4, md: 3, key: action }, {
                        default: () =>
                          h(VSheet, { class: 'pa-3 d-flex align-center ga-3', rounded: true, border: true }, {
                            default: () => [
                              h(VIcon, { icon, size: 28 }),
                              h('div', [
                                h('div', { class: 'text-subtitle-2' }, action),
                                h('div', { class: 'text-caption text-medium-emphasis' }, icon),
                              ]),
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

const meta: Meta<typeof Icons> = {
  title: 'Guidelines / Foundations / Icons',
  component: Icons,
}

export default meta
type Story = StoryObj<typeof Icons>

export const Default: Story = {}
