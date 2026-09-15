import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { computed, defineComponent, h, ref, type PropType } from 'vue'
import { VBtn, VCard, VCardText, VCardTitle } from 'vuetify/components'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import { note } from './storyNote'

// This demonstrates the pattern using the actual shared `ConfirmDialog`
// component, so the guideline example and the library implementation can
// never drift apart. The contract it shows:
//
//   1. Cancel takes focus, so a stray Enter cancels instead of deleting.
//   2. Escape and a backdrop click resolve as *cancelled*, not as nothing.
//   3. Only destructive confirmation uses `error`; high-impact confirmation
//      uses `primary`. Neither confirming action is the focused default.
type Kind = 'destructive' | 'highImpact'

const prompts = {
  destructive: {
    title: 'Delete workflow "Lung Segmentation"?',
    text: 'This also deletes all jobs belonging to the workflow.',
    triggerText: 'Delete workflow',
    confirmText: 'Delete workflow',
    color: 'error',
  },
  highImpact: {
    title: 'Download dataset (86 GB)?',
    text: 'The download may take several hours and use significant network bandwidth and local storage.',
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
              default: () => (props.kind === 'destructive' ? 'Destructive action' : 'High-impact action'),
            }),
            h(VCardText, null, {
              default: () => [
                h(VBtn, { color: prompt.value.color, onClick: () => (open.value = true) }, {
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
        h(ConfirmDialog, {
          modelValue: open.value,
          'onUpdate:modelValue': (value: boolean) => (open.value = value),
          title: prompt.value.title,
          text: prompt.value.text,
          confirmText: prompt.value.confirmText,
          color: prompt.value.color,
          onConfirm: () => (last.value = 'confirmed'),
          onCancel: () => (last.value = 'cancelled'),
        }),
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
