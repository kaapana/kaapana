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
      // Which event the dialog resolved with, so the outcome is visible.
      const outcome = ref('')
      return { args, open, outcome }
    },
    template: `
      <div>
        <VBtn :color="args.color" @click="open = true">Open confirmation</VBtn>
        <span class="ml-4 text-body-2" data-testid="confirm-outcome">{{ outcome ? 'Last outcome: ' + outcome : '' }}</span>
        <ConfirmDialog v-bind="args" v-model="open" @confirm="outcome = 'confirm'" @cancel="outcome = 'cancel'" />
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
