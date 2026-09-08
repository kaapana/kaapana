import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { defineComponent, h, ref } from 'vue'
import {
  VAutocomplete,
  VCard,
  VCardText,
  VSelect,
  VTextField,
  VTextarea,
} from 'vuetify/components'
import { note } from './storyNote'

// Deliberately sets no appearance props: the fields render with Vuetify's
// defaults instead of being restyled at each call site.
const modalities = ['CT', 'MR', 'PT', 'US']

const FormControls = defineComponent({
  name: 'FormControls',
  setup() {
    const name = ref('')
    const notes = ref('')
    const modality = ref<string | null>(null)
    const tags = ref<string[]>([])

    return () =>
      h('div', [
        note(
          'Match the control to the data: a plain select for a short closed list, ' +
            'a searchable one for a long list, free-form entry only where values outside the list are valid. ' +
            'No appearance props are set here; the controls use Vuetify’s default field style.',
        ),
        h(VCard, null, {
          default: () =>
            h(VCardText, null, {
              default: () => [
                h(VTextField, {
                  label: 'Dataset name',
                  modelValue: name.value,
                  'onUpdate:modelValue': (v: string) => (name.value = v),
                }),
                h(VSelect, {
                  label: 'Modality',
                  items: modalities,
                  modelValue: modality.value,
                  'onUpdate:modelValue': (v: string | null) => (modality.value = v),
                }),
                h(VAutocomplete, {
                  label: 'Tags',
                  items: modalities,
                  multiple: true,
                  chips: true,
                  closableChips: true,
                  modelValue: tags.value,
                  'onUpdate:modelValue': (v: string[]) => (tags.value = v),
                }),
                h(VTextarea, {
                  label: 'Notes',
                  rows: 2,
                  modelValue: notes.value,
                  'onUpdate:modelValue': (v: string) => (notes.value = v),
                }),
              ],
            }),
        }),
      ])
  },
})

const meta: Meta<typeof FormControls> = {
  title: 'Guidelines / Forms / Controls',
  component: FormControls,
}

export default meta
type Story = StoryObj<typeof FormControls>

export const Default: Story = {}
