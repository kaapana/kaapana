import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { defineComponent, h } from 'vue'
import { getProjectBase, getProjectSlug } from './selectedProject'

// The Storybook URL carries no /project/ prefix, so both helpers report unscoped.
const SelectedProjectDemo = defineComponent({
  name: 'SelectedProjectDemo',
  setup() {
    return () =>
      h('dl', [
        h('dt', 'getProjectSlug()'),
        h('dd', h('code', JSON.stringify(getProjectSlug()))),
        h('dt', 'getProjectBase()'),
        h('dd', h('code', JSON.stringify(getProjectBase()))),
      ])
  },
})

const meta: Meta<typeof SelectedProjectDemo> = {
  title: 'selectedProject',
  component: SelectedProjectDemo,
}

export default meta
type Story = StoryObj<typeof SelectedProjectDemo>

export const Default: Story = {}
