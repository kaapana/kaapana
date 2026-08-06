import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { defineComponent, h } from 'vue'
import { VChip } from 'vuetify/components'
import { kaapanaThemeLight, kaapanaThemeDark } from './vuetifyTheme'

const ThemePalette = defineComponent({
  name: 'ThemePalette',
  setup() {
    const row = (label: string, colors: Record<string, string | undefined>) =>
      h('div', { style: 'margin-bottom: 12px' }, [
        h('strong', label),
        h(
          'div',
          { style: 'display: flex; gap: 8px; flex-wrap: wrap; margin-top: 4px' },
          Object.entries(colors).map(([name, value]) =>
            h(VChip, { style: `background:${value}; color:#fff` }, () => `${name} ${value}`),
          ),
        ),
      ])
    return () =>
      h('div', [
        row('kaapanaThemeLight', kaapanaThemeLight.colors as Record<string, string>),
        row('kaapanaThemeDark', kaapanaThemeDark.colors as Record<string, string>),
      ])
  },
})

const meta: Meta<typeof ThemePalette> = {
  title: 'vuetifyTheme',
  component: ThemePalette,
}

export default meta
type Story = StoryObj<typeof ThemePalette>

export const Default: Story = {}
