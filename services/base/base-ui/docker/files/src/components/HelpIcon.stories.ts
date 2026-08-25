import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { HelpIcon } from './HelpIcon'

const meta: Meta<typeof HelpIcon> = {
  title: 'Library / HelpIcon',
  component: HelpIcon,
}

export default meta
type Story = StoryObj<typeof HelpIcon>

export const Default: Story = {
  args: { text: 'On which instances do you want to execute the workflow?' },
}
