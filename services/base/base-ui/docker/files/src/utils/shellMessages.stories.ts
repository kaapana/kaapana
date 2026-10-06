import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { defineComponent, h } from 'vue'
import { VBtn, VTable } from 'vuetify/components'
import { note } from '../reference/storyNote'
import { switchProject } from './selectedProject'
import { navigateShell } from './shellNavigation'
import { refreshShell } from './shellRefresh'

// The three requests a view can send to the portal-ui shell. Each helper posts
// one message to window.parent. In Storybook the parent is the manager frame,
// which ignores the message, so the buttons are safe to press.
const helpers = [
  {
    call: "switchProject('resb')",
    message: "{ type: 'kaapana:project-switch', slug: 'resb' }",
    effect:
      'The shell swaps the /project/<short_id> prefix, after its unsaved-changes confirm, and ' +
      'reloads the iframe. A slug it has not polled yet triggers one project-list refresh first.',
    run: () => switchProject('resb'),
  },
  {
    call: "navigateShell('/web/workflows/workflows')",
    message: "{ type: 'kaapana:navigate', path: '/web/workflows/workflows' }",
    effect:
      'The shell opens the entry, or shows "View unavailable" when the menu has no such entry ' +
      'for this user. "/web/-/<entry>" addresses a top-level entry.',
    run: () => navigateShell('/web/workflows/workflows'),
  },
  {
    call: 'refreshShell()',
    message: "{ type: 'kaapana:shell-refresh' }",
    effect:
      'The shell re-reads the menu (skipping the ingress cache) and the project list. Bursts ' +
      'within 2 s collapse into one read.',
    run: () => refreshShell(),
  },
]

const ShellMessages = defineComponent({
  name: 'ShellMessages',
  setup() {
    return () =>
      h('div', [
        note(
          'A view never navigates the top window itself. It asks the shell, which keeps its ' +
            'unsaved-changes guard and its menu in charge.',
        ),
        h(
          VTable,
          { density: 'comfortable' },
          {
            default: () => [
              h('thead', [
                h('tr', [
                  h('th', 'Helper'),
                  h('th', 'Message posted'),
                  h('th', 'What the shell does'),
                  h('th', ''),
                ]),
              ]),
              h(
                'tbody',
                helpers.map((row) =>
                  h('tr', { key: row.call }, [
                    h('td', h('code', row.call)),
                    h('td', h('code', row.message)),
                    h('td', row.effect),
                    h(
                      'td',
                      h(
                        VBtn,
                        { size: 'small', variant: 'tonal', onClick: row.run },
                        { default: () => 'Send' },
                      ),
                    ),
                  ]),
                ),
              ),
            ],
          },
        ),
      ])
  },
})

const meta: Meta<typeof ShellMessages> = {
  title: 'Library / shell messages',
  component: ShellMessages,
}

export default meta
type Story = StoryObj<typeof ShellMessages>

export const Default: Story = {}
