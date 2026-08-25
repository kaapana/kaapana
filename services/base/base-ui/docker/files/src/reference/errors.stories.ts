import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { defineComponent, h } from 'vue'
import { VAlert, VCard, VCardText, VCardTitle } from 'vuetify/components'
import { note } from './storyNote'

// Both alerts describe the same failure: a 409 from the workflow delete endpoint.
// One is what the server said, the other is what the user can act on.
const examples = [
  {
    label: 'What the transport said',
    text: 'Request failed with status code 409',
  },
  {
    label: 'What the user can act on',
    text: 'Could not delete the workflow. It is still running — abort it first.',
  },
] as const

const Errors = defineComponent({
  name: 'Errors',
  setup() {
    return () =>
      h('div', [
        note(
          'Explain what failed and, when possible, what the user can do next. Keep technical details ' +
            'in logs, and pair the error color with an icon and understandable text.',
        ),
        h(VCard, null, {
          default: () => [
            h(VCardTitle, null, { default: () => 'Same failure, different message' }),
            h(VCardText, null, {
              default: () =>
                examples.map((e) =>
                  h('div', { class: 'mb-4', key: e.label }, [
                    h('div', { class: 'text-caption text-medium-emphasis mb-1' }, e.label),
                    h(VAlert, { type: 'error', variant: 'tonal' }, { default: () => e.text }),
                  ]),
                ),
            }),
          ],
        }),
      ])
  },
})

const meta: Meta<typeof Errors> = {
  title: 'Guidelines / Feedback / Errors',
  component: Errors,
}

export default meta
type Story = StoryObj<typeof Errors>

export const Default: Story = {}
