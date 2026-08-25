import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { WorkflowExecution } from '../workflowExecution'

// The backend calls fired on mount have no responder in Storybook, so stories
// render only the empty execution-card shell.
const meta: Meta<typeof WorkflowExecution> = {
  title: 'Library / WorkflowExecution',
  component: WorkflowExecution,
}

export default meta
type Story = StoryObj<typeof WorkflowExecution>

export const Default: Story = {
  args: {},
}

export const Dialog: Story = {
  args: { isDialog: true },
}
