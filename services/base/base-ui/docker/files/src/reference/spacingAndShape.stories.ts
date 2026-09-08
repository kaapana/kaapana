import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { defineComponent, h } from 'vue'
import { VCard, VCardText, VCardTitle, VCol, VRow } from 'vuetify/components'
import { note } from './storyNote'

// This is the handbook's initial proposal. The reference sets the values
// explicitly so the proposed spacing, radius, and elevation scale can be
// evaluated together before they are adopted as platform defaults.
const steps = [
  [0, 'Flat', 'Content inside an already raised surface. Pair with a border.'],
  [2, 'Raised', 'The resting state for a card.'],
  [5, 'Overlay', 'Menus and dialogs, floating above everything.'],
] as const

const SpacingAndShape = defineComponent({
  name: 'SpacingAndShape',
  setup() {
    return () =>
      h('div', [
        note(
          'Initial proposal: use the 4 px spacing scale, an 8 px default corner radius, and ' +
            'elevations 0, 2, and 5. These values are still to be decided; the examples below ' +
            'make the proposal visible for comparison.',
        ),
        h(VRow, null, {
          default: () =>
            steps.map(([elevation, label, text]) =>
              h(VCol, { cols: 12, md: 4, key: label }, {
                default: () =>
                  h(VCard, { elevation, border: elevation === 0, rounded: 'lg' }, {
                    default: () => [
                      h(VCardTitle, null, { default: () => `${label} — elevation ${elevation}` }),
                      h(VCardText, { class: 'pa-4' }, { default: () => text }),
                    ],
                  }),
              }),
            ),
        }),
      ])
  },
})

const meta: Meta<typeof SpacingAndShape> = {
  title: 'Guidelines / Foundations / Spacing & Shape',
  component: SpacingAndShape,
}

export default meta
type Story = StoryObj<typeof SpacingAndShape>

export const Default: Story = {}
