import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { defineComponent, h, ref } from 'vue'
import {
  VAlert,
  VBtn,
  VCard,
  VCardActions,
  VCardText,
  VCardTitle,
  VForm,
  VSpacer,
  VTextField,
} from 'vuetify/components'
import { note } from './storyNote'

// The rule being shown is about the *message*, not the mechanism: say what is
// required, not merely that something is wrong.
const NAME_PATTERN = /^[a-z0-9]+-[a-z0-9]+$/

const helpful = [
  (v: string) => !!v || 'A name is required.',
  (v: string) => !v || (v.length >= 3 && v.length <= 30) || 'Use 3–30 characters.',
  (v: string) =>
    !v ||
    NAME_PATTERN.test(v) ||
    'Use exactly one hyphen, with lowercase letters or digits on both sides; do not end with a hyphen.',
]

const unhelpful = [
  (v: string) =>
    (!!v && v.length >= 3 && v.length <= 30 && NAME_PATTERN.test(v)) || 'Invalid input.',
]

const Validation = defineComponent({
  name: 'Validation',
  setup() {
    const good = ref('')
    const bad = ref('')
    return () =>
      h('div', [
        note(
          'Validation should explain how to correct a value. Both fields enforce the rules below, ' +
            'but only the helpful field gives actionable messages. Try “My Dataset”, an ending ' +
            'hyphen, or more than 30 characters to compare them.',
        ),
        h(VCard, null, {
          default: () => [
            h(VCardTitle, null, { default: () => 'Same validity, different message' }),
            h(VCardText, null, {
              default: () =>
                h(VForm, null, {
                  default: () => [
                    h(VAlert, {
                      type: 'info',
                      variant: 'tonal',
                      class: 'mb-4',
                      title: 'Example rules',
                      text: 'Required · 3–30 characters · exactly one hyphen · lowercase letters and digits on both sides · no ending hyphen',
                    }),
                    h('div', { class: 'd-flex ga-6 flex-wrap' }, [
                      h('div', { style: 'flex: 1 1 260px' }, [
                        h('div', { class: 'text-caption text-medium-emphasis mb-1' }, 'Helpful'),
                        h(VTextField, {
                          label: 'Dataset name',
                          rules: helpful,
                          modelValue: good.value,
                          'onUpdate:modelValue': (v: string) => (good.value = v),
                        }),
                      ]),
                      h('div', { style: 'flex: 1 1 260px' }, [
                        h('div', { class: 'text-caption text-medium-emphasis mb-1' }, 'Unhelpful'),
                        h(VTextField, {
                          label: 'Dataset name',
                          rules: unhelpful,
                          modelValue: bad.value,
                          'onUpdate:modelValue': (v: string) => (bad.value = v),
                        }),
                      ]),
                    ]),
                  ],
                }),
            }),
            h(VCardActions, null, {
              default: () => [h(VSpacer), h(VBtn, { color: 'primary' }, { default: () => 'Save' })],
            }),
          ],
        }),
      ])
  },
})

const meta: Meta<typeof Validation> = {
  title: 'Guidelines / Forms / Validation',
  component: Validation,
}

export default meta
type Story = StoryObj<typeof Validation>

export const Default: Story = {}
