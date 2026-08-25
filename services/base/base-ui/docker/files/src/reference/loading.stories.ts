import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { defineComponent, h, onBeforeUnmount, ref } from 'vue'
import {
  VBtn, VCard, VCardActions, VCardText, VCardTitle, VCol, VDataTable, VRow, VSkeletonLoader, VSpacer,
} from 'vuetify/components'
import { note } from './storyNote'

const headers = [
  { title: 'Workflow', key: 'workflow' },
  { title: 'Status', key: 'status' },
]

const Loading = defineComponent({
  name: 'Loading',
  setup() {
    const saving = ref(false)
    let timer: ReturnType<typeof setTimeout> | undefined
    let initialTimer: ReturnType<typeof setTimeout> | undefined

    // The button disables itself while running, which is what stops a second
    // submission of the same mutation — the guideline's rule, and the reason the
    // loading state is not merely decorative.
    function save() {
      if (saving.value) return
      saving.value = true
      timer = setTimeout(() => (saving.value = false), 2500)
    }

    // Same idea for the skeleton: flip it to watch the swap, and note the layout
    // does not jump — that is what "shaped like the content" buys.
    const pending = ref(true)
    let reloadTimer: ReturnType<typeof setTimeout> | undefined

    function reload() {
      if (pending.value) return
      pending.value = true
      reloadTimer = setTimeout(() => (pending.value = false), 1800)
    }

    initialTimer = setTimeout(() => (pending.value = false), 1200)

    onBeforeUnmount(() => {
      clearTimeout(timer)
      clearTimeout(initialTimer)
      clearTimeout(reloadTimer)
    })

    return () =>
      h('div', [
        note(
          'Use a content-shaped placeholder for initial loading, keep tables visible while rows ' +
            'load, and show mutation progress on the action that started it. Disable that action ' +
            'while it runs to prevent duplicate submissions.',
        ),
        h(VRow, null, {
          default: () => [
            h(VCol, { cols: 12, md: 6 }, {
              default: () =>
                h(VCard, null, {
                  default: () => [
                    h(VCardTitle, null, { default: () => 'Initial content' }),
                    h(VCardText, null, {
                      default: () => [
                        // The real content goes in the default slot and the
                        // skeleton replaces it while `loading` is true, so a view
                        // needs one template rather than a loading branch and a
                        // loaded branch. `type` is a shape description — commas
                        // compose presets, `@n` repeats them — not hand-drawn
                        // boxes, but also not derived from the children: nothing
                        // keeps it in step if the content below changes.
                        h(VSkeletonLoader, { loading: pending.value, type: 'article, actions' }, {
                          default: () => [
                            h('div', { class: 'text-h6 mb-2' }, 'Lung Segmentation'),
                            h('p', { class: 'text-body-2 mb-4' },
                              'Fourteen series, acquired between March and July. Last run two days ago.'),
                            h('div', { class: 'd-flex ga-2' }, [
                              h(VBtn, { size: 'small', variant: 'text' }, () => 'Details'),
                              h(VBtn, { size: 'small', color: 'primary' }, () => 'Run'),
                            ]),
                          ],
                        }),
                        h(VBtn, {
                          class: 'mt-4',
                          size: 'small',
                          variant: 'outlined',
                          onClick: reload,
                        }, { default: () => (pending.value ? 'Loading…' : 'Reload') }),
                      ],
                    }),
                  ],
                }),
            }),
            h(VCol, { cols: 12, md: 6 }, {
              default: () =>
                h(VCard, null, {
                  default: () => [
                    h(VCardTitle, null, { default: () => 'A table fetching rows' }),
                    h(VDataTable, { headers, items: [], loading: true, density: 'compact' }),
                  ],
                }),
            }),
            h(VCol, { cols: 12 }, {
              default: () =>
                h(VCard, null, {
                  default: () => [
                    h(VCardTitle, null, { default: () => 'A mutation in progress' }),
                    h(VCardText, null, {
                      default: () =>
                        'The control that started the work shows the work. A destructive action ' +
                        'must never look inert after it is triggered.',
                    }),
                    h(VCardActions, null, {
                      default: () => [
                        h(VSpacer),
                        h(VBtn, null, { default: () => 'Cancel' }),
                        h(VBtn, {
                          color: 'primary',
                          loading: saving.value,
                          disabled: saving.value,
                          onClick: save,
                        }, { default: () => 'Save' }),
                      ],
                    }),
                  ],
                }),
            }),
          ],
        }),
      ])
  },
})

const meta: Meta<typeof Loading> = {
  title: 'Guidelines / Feedback / Loading',
  component: Loading,
}

export default meta
type Story = StoryObj<typeof Loading>

export const Default: Story = {}
