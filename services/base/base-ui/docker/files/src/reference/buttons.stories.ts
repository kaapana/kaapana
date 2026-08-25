import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { defineComponent, h } from 'vue'
import { VBtn, VCard, VCardActions, VCardText, VCardTitle, VSpacer, VTooltip } from 'vuetify/components'
import { note } from './storyNote'

// The four levels of the action hierarchy, shown twice: standing alone, and
// inside a card action row. Vuetify's own VCardActions provides
// variant="text" to the buttons beneath it, so the same markup renders
// differently in the two places. That is deliberate and worth seeing: the
// appearance varies with context, the meaning does not.
//
// Emphasis is carried by `color`. No call site below sets `variant` except the
// tertiary action, where low emphasis is the point.
const level = (label: string, props: Record<string, unknown>) => h(VBtn, props, () => label)

// A disabled control that does not say why is a dead end, so the disabled example
// carries its reason. Note the wrapper: a disabled button receives no pointer
// events, so a tooltip attached to the button itself never opens — the activator
// has to be the element around it. The label below is a placeholder on purpose;
// the real string names the specific condition, not the fact of being disabled.
const unavailable = () =>
  h(VTooltip, { location: 'top', text: 'Select a project before running a workflow.' }, {
    activator: ({ props }: { props: Record<string, unknown> }) =>
      h('span', props, [h(VBtn, { disabled: true }, () => 'Unavailable')]),
  })

const hierarchy = () => [
  level('Run workflow', { color: 'primary' }),
  level('Cancel', {}),
  level('Details', { variant: 'text' }),
  level('Delete workflow', { color: 'error' }),
  unavailable(),
]

const Buttons = defineComponent({
  name: 'Buttons',
  setup() {
    return () =>
      h('div', [
        note(
          'Distinguish primary, secondary, tertiary, destructive, and unavailable actions. Keep a ' +
            'temporarily unavailable action visible and explain why; hide an action only when it ' +
            'does not apply. A task area should normally have one primary action.',
        ),
        h('div', { class: 'text-subtitle-2 mb-2' }, 'Standalone'),
        h('div', { class: 'd-flex ga-2 flex-wrap mb-6' }, hierarchy()),
        h(VCard, null, {
          default: () => [
            h(VCardTitle, () => 'In a card action row'),
            h(VCardText, () => 'One clearly identifiable primary action per task area.'),
            h(VCardActions, null, { default: () => [h(VSpacer), ...hierarchy()] }),
          ],
        }),
      ])
  },
})

const meta: Meta<typeof Buttons> = {
  title: 'Guidelines / Actions / Buttons',
  component: Buttons,
}

export default meta
type Story = StoryObj<typeof Buttons>

export const Default: Story = {}
