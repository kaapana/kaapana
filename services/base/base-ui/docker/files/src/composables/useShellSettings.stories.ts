import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { defineComponent, h } from 'vue'
import { VBtn } from 'vuetify/components'
import { useTheme } from 'vuetify'
import { useShellSettings } from './useShellSettings'

// A same-document localStorage write never fires a 'storage' event, so the
// buttons dispatch a synthetic one to mimic the shell writing it.
const ShellSettingsDemo = defineComponent({
  name: 'ShellSettingsDemo',
  setup() {
    // Map onto Storybook's default vuetify theme names so dark mode visibly toggles.
    const { viewKey } = useShellSettings({ lightTheme: 'light', darkTheme: 'dark' })
    const theme = useTheme()

    const write = (next: Record<string, unknown>) => {
      const oldValue = localStorage['settings'] || null
      const newValue = JSON.stringify(next)
      localStorage['settings'] = newValue
      window.dispatchEvent(new StorageEvent('storage', { key: 'settings', oldValue, newValue }))
    }

    return () =>
      h('div', { style: 'display: flex; flex-direction: column; gap: 8px; max-width: 320px' }, [
        h(VBtn, { onClick: () => write({ darkMode: theme.global.name.value !== 'dark' }) }, () =>
          'Toggle darkMode (live)',
        ),
        h(VBtn, { onClick: () => write({ darkMode: theme.global.name.value === 'dark', tick: Date.now() }) }, () =>
          'Change other setting (remounts view)',
        ),
        h('code', `theme: ${theme.global.name.value} | viewKey: ${viewKey.value}`),
      ])
  },
})

const meta: Meta<typeof ShellSettingsDemo> = {
  title: 'useShellSettings',
  component: ShellSettingsDemo,
}

export default meta
type Story = StoryObj<typeof ShellSettingsDemo>

export const Default: Story = {}
