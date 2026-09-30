import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { defineComponent, h, ref } from 'vue'
import { VAlert, VBtn, VCard, VCardText, VCardTitle } from 'vuetify/components'
import ErrorDetailsDialog from '../components/ErrorDetailsDialog.vue'
import type { ApiErrorInfo } from '../utils/apiErrors'
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

// The technical detail is not thrown away: it moves behind a disclosure the
// user can open and copy, rendered by the shared ErrorDetailsDialog.
const detail: ApiErrorInfo = {
  status: 409,
  statusText: 'Conflict',
  method: 'DELETE',
  url: '/kaapana-backend/client/workflow/lung-segmentation-250917',
  detail: 'Workflow lung-segmentation-250917 has 3 running jobs',
  requestId: null,
  message: 'Request failed with status code 409',
}

const Errors = defineComponent({
  name: 'Errors',
  setup() {
    const open = ref(false)
    return () =>
      h('div', [
        note(
          'Explain what failed and, when possible, what the user can do next. Keep the backend ' +
            'message, status code and request identifier reachable behind a disclosure rather ' +
            'than shown by default, and pair the error color with an icon and understandable text.',
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
        h(VCard, { class: 'mt-4' }, {
          default: () => [
            h(VCardTitle, null, { default: () => 'Technical detail on demand' }),
            h(VCardText, null, {
              default: () => [
                h(
                  VAlert,
                  { type: 'error', variant: 'tonal' },
                  {
                    default: () => 'Could not delete the workflow. It is still running — abort it first.',
                    append: () =>
                      h(VBtn, { variant: 'text', size: 'small', onClick: () => (open.value = true) }, {
                        default: () => 'Details',
                      }),
                  },
                ),
                h(ErrorDetailsDialog, {
                  modelValue: open.value,
                  'onUpdate:modelValue': (value: boolean) => (open.value = value),
                  title: 'Workflow not deleted',
                  text: 'Could not delete the workflow. It is still running — abort it first.',
                  error: detail,
                }),
              ],
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
