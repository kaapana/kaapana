import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { defineComponent, h } from 'vue'
import { note } from './storyNote'

// The platform type scale is Vuetify's, used through its classes. This page
// exists so a hierarchy can be chosen by looking rather than by guessing which
// class is one step down.
const scale = [
  ['text-h4', 'Page title'],
  ['text-h5', 'Section title'],
  ['text-h6', 'Content title'],
  ['text-subtitle-1', 'Supporting subtitle'],
  ['text-body-1', 'Body text'],
  ['text-body-2', 'Secondary body text'],
  ['text-caption', 'Caption and helper text'],
  ['text-overline', 'Overline'],
] as const

const Typography = defineComponent({
  name: 'Typography',
  setup() {
    return () =>
      h('div', [
        note(
          'Use Vuetify type classes instead of one-off font sizes. Use size and weight for hierarchy, ' +
            'and use the emphasis classes for supporting or inactive content.',
        ),
        ...scale.map(([cls, label]) =>
          h('div', { class: `${cls} mb-2`, key: cls }, `${cls} — ${label}`),
        ),
        h('div', { class: 'mt-6' }, [
          h('div', { class: 'text-body-1' }, 'High emphasis — default body color'),
          h('div', { class: 'text-body-1 text-medium-emphasis' }, 'Medium emphasis — supporting information'),
          h('div', { class: 'text-body-1 text-disabled' }, 'Disabled emphasis — inactive content'),
        ]),
      ])
  },
})

const meta: Meta<typeof Typography> = {
  title: 'Guidelines / Foundations / Typography',
  component: Typography,
}

export default meta
type Story = StoryObj<typeof Typography>

export const Default: Story = {}
