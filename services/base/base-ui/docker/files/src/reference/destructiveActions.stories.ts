import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { computed, defineComponent, h, ref, type PropType } from 'vue'
import { VBtn, VCard, VCardActions, VCardText, VCardTitle, VDialog, VSpacer } from 'vuetify/components'
import { note } from './storyNote'

// The example demonstrates the confirmation contract:
//
//   1. Cancel takes focus, so a stray Enter cancels instead of deleting.
//   2. Escape and a backdrop click resolve as *cancelled*, not as nothing.
//   3. Only destructive confirmation uses `error`; high-impact confirmation
//      uses `primary`. Neither confirming action is the focused default.
type Kind = 'destructive' | 'highImpact'

const prompts = {
  destructive: {
    title: 'Delete workflow "Lung Segmentation"?',
    consequence: 'This also deletes all jobs belonging to the workflow.',
    triggerText: 'Delete workflow',
    confirmText: 'Delete workflow',
    color: 'error',
  },
  highImpact: {
    title: 'Download dataset (86 GB)?',
    consequence:
      'The download may take several hours and use significant network bandwidth and local storage.',
    triggerText: 'Download Dataset',
    confirmText: 'Download',
    color: 'primary',
  },
} as const

const ActionsRequiringConfirmation = defineComponent({
  name: 'ActionsRequiringConfirmation',
  props: {
    kind: {
      type: String as PropType<Kind>,
      required: true,
    },
  },
  setup(props) {
    const open = ref(false)
    const last = ref('—')
    const prompt = computed(() => prompts[props.kind])

    function ask() {
      open.value = true
    }

    function resolve(confirmed: boolean) {
      open.value = false
      last.value = confirmed ? 'confirmed' : 'cancelled'
    }

    return () =>
      h('div', [
        note(
          props.kind === 'destructive'
            ? 'Confirm actions that permanently remove data or are difficult to reverse. Use the error color only for the destructive action, and give initial focus to Cancel.'
            : 'Confirm reversible actions when users could overlook their scale or resource cost. State the expected time, bandwidth, storage, or compute impact; use the primary color and give initial focus to Cancel.',
        ),
        h(VCard, null, {
          default: () => [
            h(VCardTitle, null, {
              default: () =>
                props.kind === 'destructive' ? 'Destructive action' : 'High-impact action',
            }),
            h(VCardText, null, {
              default: () => [
                h(VBtn, { color: prompt.value.color, onClick: ask }, {
                  default: () => prompt.value.triggerText,
                }),
                h('div', { class: 'mt-4 text-body-2 text-medium-emphasis' }, [
                  'Last answer: ',
                  h('strong', last.value),
                ]),
              ],
            }),
          ],
        }),
        h(
          VDialog,
          {
            modelValue: open.value,
            maxWidth: 400,
            // Escape and the backdrop route through the same path as Cancel, so a
            // dismissed prompt is an answer rather than a dangling state.
            'onUpdate:modelValue': (value: boolean) => {
              if (!value) resolve(false)
            },
          },
          {
            default: () =>
              h(VCard, null, {
                default: () => [
                  h(VCardTitle, null, { default: () => prompt.value.title }),
                  h(VCardText, null, { default: () => prompt.value.consequence }),
                  h(VCardActions, null, {
                    default: () => [
                      h(VSpacer),
                      h(VBtn, { autofocus: true, onClick: () => resolve(false) }, {
                        default: () => 'Cancel',
                      }),
                      h(VBtn, { color: prompt.value.color, onClick: () => resolve(true) }, {
                        default: () => prompt.value.confirmText,
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

const meta: Meta<typeof ActionsRequiringConfirmation> = {
  title: 'Guidelines / Patterns / Actions Requiring Confirmation',
  component: ActionsRequiringConfirmation,
}

export default meta
type Story = StoryObj<typeof ActionsRequiringConfirmation>

export const Destructive: Story = {
  args: { kind: 'destructive' },
}

export const HighImpact: Story = {
  args: { kind: 'highImpact' },
}
