import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { defineComponent, h } from 'vue'
import { notify } from '@kyvg/vue3-notification'
import { VAlert, VBtn, VCard, VCardText, VCardTitle, VCol, VRow, VSheet } from 'vuetify/components'
import { note } from './storyNote'

// Transient notifications use the platform's existing notification library.
// Storybook can demonstrate the non-expiring local presentation. API-backed
// persistence is described rather than mocked so the example does not imply
// that a platform integration already exists.
const transient = [
  { type: 'success', label: 'success', title: 'Dataset saved.' },
  { type: 'info', label: 'info', title: 'Two jobs are still running.' },
  { type: 'warn', label: 'warning', title: 'Results are incomplete.' },
] as const

const inline = [
  { type: 'warning', text: 'Results are incomplete: two jobs are still running.' },
  { type: 'info', text: 'This project is read-only for your role.' },
] as const

const NotificationsAndAlerts = defineComponent({
  name: 'NotificationsAndAlerts',
  setup() {
    return () =>
      h('div', [
        note(
          'Use transient notifications for recent outcomes and inline alerts for conditions tied ' +
            'to the current content. Persistent notification behavior is still to be decided. ' +
            'Compare the three proposals below: local, API-backed, or combined.',
        ),
        h(VRow, null, {
          default: () => [
            h(VCol, { cols: 12, md: 4 }, {
              default: () =>
                h(VCard, null, {
                  default: () => [
                    h(VCardTitle, null, { default: () => 'Transient — the outcome of an action' }),
                    h(VCardText, null, {
                      default: () => [
                        h('p', { class: 'text-body-2 text-medium-emphasis mb-3' },
                          'Brief feedback about an action that just completed.'),
                        h('div', { class: 'd-flex ga-2 flex-wrap' },
                          transient.map((t) =>
                            h(VBtn, { key: t.type, onClick: () => notify({ type: t.type, title: t.title }) },
                              { default: () => t.label }),
                          ),
                        ),
                      ],
                    }),
                  ],
                }),
            }),
            h(VCol, { cols: 12, md: 4 }, {
              default: () =>
                h(VCard, null, {
                  default: () => [
                    h(VCardTitle, null, { default: () => 'Persistent — to be decided' }),
                    h(VCardText, null, {
                      default: () => [
                        h(VSheet, { border: true, rounded: true, class: 'pa-3 mb-3' }, {
                          default: () => [
                            h('div', { class: 'text-subtitle-2' }, '1. Non-expiring notification'),
                            h('p', { class: 'text-body-2 text-medium-emphasis my-2' },
                              'Uses the transient presentation and remains until clicked. It does not survive a reload or session change.'),
                            h(VBtn, {
                              size: 'small',
                              onClick: () =>
                                notify({
                                  type: 'info',
                                  title: 'A platform update is available. Click to mark it as read.',
                                  duration: -1,
                                }),
                            }, { default: () => 'Try local proposal' }),
                          ],
                        }),
                        h(VSheet, { border: true, rounded: true, class: 'pa-3 mb-3' }, {
                          default: () => [
                            h('div', { class: 'text-subtitle-2' }, '2. Kaapana notifications API'),
                            h('p', { class: 'text-body-2 text-medium-emphasis my-2 mb-0' },
                              'Stores the notification and its read state centrally so it remains available across views and sessions.'),
                          ],
                        }),
                        h(VSheet, { border: true, rounded: true, class: 'pa-3' }, {
                          default: () => [
                            h('div', { class: 'text-subtitle-2' }, '3. Combined'),
                            h('p', { class: 'text-body-2 text-medium-emphasis my-2 mb-0' },
                              'Stores the notification through the API and also shows it immediately. Clicking the local notification marks the stored one as read.'),
                          ],
                        }),
                      ],
                    }),
                  ],
                }),
            }),
            h(VCol, { cols: 12, md: 4 }, {
              default: () =>
                h(VCard, null, {
                  default: () => [
                    h(VCardTitle, null, { default: () => 'Inline — a condition of this content' }),
                    h(VCardText, null, {
                      default: () =>
                        inline.map((a) =>
                          h(VAlert, { key: a.type, type: a.type, variant: 'tonal', class: 'mb-3' },
                            { default: () => a.text }),
                        ),
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
