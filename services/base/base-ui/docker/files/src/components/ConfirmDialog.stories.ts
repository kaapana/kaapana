import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { ref } from 'vue'
import { VBtn } from 'vuetify/components'
import ConfirmDialog from './ConfirmDialog.vue'

const meta: Meta<typeof ConfirmDialog> = {
  title: 'Library / ConfirmDialog',
  component: ConfirmDialog,
  render: (args) => ({
    components: { ConfirmDialog, VBtn },
    setup() {
      const open = ref(false)
      return { args, open }
    },
    template: `
      <div>
        <VBtn :color="args.color" @click="open = true">Open confirmation</VBtn>
        <ConfirmDialog v-bind="args" v-model="open" />
      </div>
    `,
  }),
}

export default meta
type Story = StoryObj<typeof ConfirmDialog>

export const Destructive: Story = {
  args: {
    title: 'Delete workflow "Lung Segmentation"?',
    text: 'This also deletes all jobs belonging to the workflow.',
    confirmText: 'Delete workflow',
    color: 'error',
  },
}

export const HighImpact: Story = {
  args: {
    title: 'Download dataset (86 GB)?',
    text: 'The download may take several hours and use significant network bandwidth and local storage.',
    confirmText: 'Download',
    color: 'primary',
  },
}
