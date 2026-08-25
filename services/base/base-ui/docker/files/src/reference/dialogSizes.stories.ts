import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { computed, defineComponent, h, ref } from 'vue'
import {
  VBtn, VCard, VCardActions, VCardText, VCardTitle, VDialog, VSpacer, VTextField, VTextarea,
} from 'vuetify/components'
import { note } from './storyNote'

// Three widths, and nothing between them. The point of a scale is that a call
// site picks a size rather than a number: `max-width` written per dialog is how
// one view ends up with 480, another with 500 and a third with 520, all meaning
// "a form".
const sizes = {
  small: {
    width: 400,
    label: 'Small — a confirmation',
    title: 'Delete workflow "Lung Segmentation"?',
    body: 'One decision, no scrolling. Anything that needs a form is not small.',
  },
  medium: {
    width: 600,
    label: 'Medium — a form',
    title: 'Edit dataset',
    body: 'The default for editing. Wide enough for labelled fields, narrow enough to read.',
  },
  large: {
    width: 900,
    label: 'Large — content',
    title: 'Results',
    body: 'For tables, previews and comparisons. Not a substitute for a full view.',
  },
} as const

type Size = keyof typeof sizes

const DialogSizes = defineComponent({
  name: 'DialogSizes',
  setup() {
    const open = ref(false)
    const size = ref<Size>('small')
    const current = computed(() => sizes[size.value])

    function show(next: Size) {
      size.value = next
      open.value = true
    }

    return () =>
      h('div', [
        note(
          'Choose dialog width by content: 400 px for a focused decision, 600 px for a form, and ' +
            '900 px for tables, previews, or comparisons. Content that needs more space belongs ' +
            'in a full view.',
        ),
        h(VCard, null, {
          default: () => [
            h(VCardTitle, null, { default: () => 'The three widths' }),
            h(VCardText, null, {
              default: () =>
                h('div', { class: 'd-flex ga-2 flex-wrap' },
                  (Object.keys(sizes) as Size[]).map((key) =>
                    h(VBtn, { key, onClick: () => show(key) }, {
                      default: () => `${sizes[key].label} · ${sizes[key].width}`,
                    }),
                  ),
                ),
            }),
          ],
        }),
        h(
          VDialog,
          {
            modelValue: open.value,
            maxWidth: current.value.width,
            'onUpdate:modelValue': (value: boolean) => (open.value = value),
          },
          {
            default: () =>
              h(VCard, null, {
                default: () => [
                  h(VCardTitle, null, { default: () => current.value.title }),
                  h(VCardText, null, {
                    default: () => [
                      h('p', { class: 'mb-4' }, current.value.body),
                      // Only the medium dialog carries a form, to make the point
                      // that the size follows the content type.
                      ...(size.value === 'medium'
                        ? [
                            h(VTextField, { label: 'Name' }),
                            h(VTextarea, { label: 'Notes', rows: 2 }),
                          ]
                        : []),
                      h('p', { class: 'text-caption text-medium-emphasis mb-0' },
                        `max-width ${current.value.width}`),
                    ],
                  }),
                  h(VCardActions, null, {
                    default: () => [
                      h(VSpacer),
                      h(VBtn, { autofocus: true, onClick: () => (open.value = false) }, {
                        default: () => 'Close',
                      }),
                    ],
                  }),
                ],
              }),
          },
        ),
      ])
  },
})

const meta: Meta<typeof DialogSizes> = {
  title: 'Guidelines / Dialogs / Sizes',
  component: DialogSizes,
}

export default meta
type Story = StoryObj<typeof DialogSizes>

export const Default: Story = {}
