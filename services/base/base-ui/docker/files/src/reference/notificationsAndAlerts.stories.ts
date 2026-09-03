import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { defineComponent, h } from 'vue'
import { notify } from '@kyvg/vue3-notification'
import {
  VAlert,
  VBtn,
  VCard,
  VCardText,
  VCardTitle,
  VCol,
  VDivider,
  VIcon,
  VRow,
  VSheet,
} from 'vuetify/components'
import { note } from './storyNote'

// Note the two spellings below. They are not a typo: the notification library
// takes `warn`, Vuetify's v-alert takes `warning`.
const transient = [
  {
    type: 'success',
    label: 'success',
    title: 'Dataset saved',
    text: 'Cohort A is available to everyone on this project.',
  },
  {
    type: 'info',
    label: 'info',
    title: 'Import started',
    text: 'The list updates as the import progresses.',
  },
  {
    type: 'warn',
    label: 'warning',
    title: 'Nothing to download',
    text: 'Select at least one series before starting a download.',
  },
  {
    type: 'error',
    label: 'error',
    title: 'Dataset not created',
    text: 'The dataset could not be created. A dataset with this name already exists.',
  },
] as const

const inline = [
  {
    type: 'warning',
    text: 'Could not refresh the extension list — showing the last version that loaded.',
  },
  { type: 'info', text: 'This project is read-only for your role.' },
] as const

/** One row as the portal's notification center renders it. Presentation only. */
const storedNotification = () =>
  h(VSheet, { border: true, rounded: true, class: 'pa-3' }, {
    default: () => [
      h('div', { class: 'd-flex ga-3' }, [
        h(VIcon, { icon: 'mdi-check-circle', color: 'success', class: 'mt-1' }),
        h('div', [
          h('div', { class: 'text-subtitle-2' }, 'Workflow finished'),
          h('p', { class: 'text-body-2 text-medium-emphasis mb-1' },
            'nnU-Net training completed on Cohort A.'),
          h('span', { class: 'text-caption text-medium-emphasis' }, '14:02 · Mark as read'),
        ]),
      ]),
    ],
  })

const NotificationsAndAlerts = defineComponent({
  name: 'NotificationsAndAlerts',
  setup() {
    return () =>
      h('div', [
        note(
          'Choose by where the information belongs and how long it must stay available, not by ' +
            'severity: transient for the outcome of an action, inline for a condition of the ' +
            'content on screen, persistent for anything that must outlive the page. Do not show ' +
            'the same message in two of them unless it could otherwise be missed.',
        ),
        h(VRow, null, {
          default: () => [
            h(VCol, { cols: 12, md: 4 }, {
              default: () =>
                h(VCard, { height: '100%' }, {
                  default: () => [
                    h(VCardTitle, null, { default: () => 'Transient — the outcome of an action' }),
                    h(VCardText, null, {
                      default: () => [
                        h('p', { class: 'text-body-2 text-medium-emphasis mb-3' },
                          'Bottom right, five seconds. A short title naming the outcome plus a ' +
                            'complete sentence — never a status code.'),
                        h('div', { class: 'd-flex ga-2 flex-wrap' },
                          transient.map((t) =>
                            h(VBtn, {
                              key: t.type,
                              size: 'small',
                              onClick: () => notify({ type: t.type, title: t.title, text: t.text }),
                            },
                              { default: () => t.label }),
                          ),
                        ),
                        h(VDivider, { class: 'my-3' }),
                        h('p', { class: 'text-caption text-medium-emphasis mb-0' },
                          'A polled endpoint notifies once and re-arms only after a success, so a ' +
                            'lasting failure does not toast on every tick.'),
                      ],
                    }),
                  ],
                }),
            }),
            h(VCol, { cols: 12, md: 4 }, {
              default: () =>
                h(VCard, { height: '100%' }, {
                  default: () => [
                    h(VCardTitle, null, { default: () => 'Persistent — outlives the page' }),
                    h(VCardText, null, {
                      default: () => [
                        h('p', { class: 'text-body-2 text-medium-emphasis mb-3' },
                          'Created through the Kaapana notifications API. The notification ' +
                            'service stores it and its read state; the portal lists it in the ' +
                            'notification center, as below, and shows a transient notification ' +
                            'when it arrives. A view must not add a local notification for the ' +
                            'same event.'),
                        storedNotification(),
                        h('p', { class: 'text-caption text-medium-emphasis mt-3 mb-0' },
                          'Presentation only — this example is not backed by the API. Use it for ' +
                            'a finished long-running workflow or import, a shared resource ' +
                            'becoming unavailable, or anything needing attention after the user ' +
                            'has left the originating page.'),
                      ],
                    }),
                  ],
                }),
            }),
            h(VCol, { cols: 12, md: 4 }, {
              default: () =>
                h(VCard, { height: '100%' }, {
                  default: () => [
                    h(VCardTitle, null, { default: () => 'Inline — a condition of this content' }),
                    h(VCardText, null, {
                      default: () => [
                        h('p', { class: 'text-body-2 text-medium-emphasis mb-3' },
                          'Next to what it is about, for as long as it holds. The first alert ' +
                            'stays because the list on screen stays stale; a toast would claim ' +
                            'the problem had passed.'),
                        ...inline.map((a) =>
                          h(VAlert, {
                            key: a.type,
                            type: a.type,
                            variant: 'tonal',
                            density: 'compact',
                            class: 'mb-3',
                          },
                            { default: () => a.text }),
                        ),
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

const meta: Meta<typeof NotificationsAndAlerts> = {
  title: 'Guidelines / Feedback / Notifications & Alerts',
  component: NotificationsAndAlerts,
}

export default meta
type Story = StoryObj<typeof NotificationsAndAlerts>

export const Default: Story = {}
