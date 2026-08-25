import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { defineComponent, h } from 'vue'
import { VBtn, VCard, VCol, VEmptyState, VRow } from 'vuetify/components'
import { kaapanaIcons } from '../utils/icons'
import { note } from './storyNote'

// The view must distinguish an empty collection, an empty result, and a failed
// request. A presentation component cannot infer that state from an empty array.
const cases = [
  {
    label: 'Nothing yet',
    title: 'No workflows yet',
    text: 'Start a workflow to see it here.',
    icon: undefined,
    action: 'Run a workflow',
  },
  {
    label: 'Nothing matched',
    title: 'No matching workflows',
    text: 'No results for the current filters. Clear them to see everything.',
    icon: kaapanaIcons.search,
    action: 'Clear filters',
  },
  {
    label: 'Could not load',
    title: 'Could not load workflows',
    text: 'Try again, or contact your administrator if it persists.',
    icon: kaapanaIcons.error,
    action: 'Try again',
  },
] as const

const EmptyStates = defineComponent({
  name: 'EmptyStates',
  setup() {
    return () =>
      h('div', [
        note(
          'Distinguish an empty collection, no filter matches, and a failed request. Explain the ' +
            'state and offer the relevant first action, filter reset, or retry. A normal empty ' +
            'collection does not need an alert icon.',
        ),
        h(VRow, null, {
          default: () =>
            cases.map((c) =>
              h(VCol, { cols: 12, md: 4, key: c.label }, {
                default: () => [
                  h('div', { class: 'text-subtitle-2 mb-1' }, c.label),
                  h(VCard, null, {
                    default: () =>
                      h(VEmptyState, { title: c.title, text: c.text, icon: c.icon, size: 56 }, {
                        actions: () =>
                          h(VBtn, { color: 'primary', variant: 'text' }, { default: () => c.action }),
                      }),
                  }),
                ],
              }),
            ),
        }),
      ])
  },
})

const meta: Meta<typeof EmptyStates> = {
  title: 'Guidelines / Feedback / Empty States',
  component: EmptyStates,
}

export default meta
type Story = StoryObj<typeof EmptyStates>

export const Default: Story = {}
