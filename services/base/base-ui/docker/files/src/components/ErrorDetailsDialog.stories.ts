import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { ref } from 'vue'
import { notify } from '@kyvg/vue3-notification'
import { VBtn } from 'vuetify/components'
import ErrorDetailsDialog from './ErrorDetailsDialog.vue'
import type { ApiErrorInfo } from '../utils/apiErrors'

const conflict: ApiErrorInfo = {
  status: 409,
  statusText: 'Conflict',
  method: 'POST',
  url: '/kube-helm-api/helm-delete-chart',
  detail: 'Release mitk-workbench-abc123 is being upgraded, try again later',
  requestId: 'c1f3a2e4-7b1d-4a9e-9f2c-0d5e6a7b8c9d',
  message: 'Request failed with status code 409',
}

const meta: Meta<typeof ErrorDetailsDialog> = {
  title: 'Library / ErrorDetailsDialog',
  component: ErrorDetailsDialog,
  render: (args) => ({
    components: { ErrorDetailsDialog, VBtn },
    setup() {
      const open = ref(false)
      // The pattern end to end: the transient notification says what failed,
      // and selecting it opens the disclosure that stays until closed.
      function fail() {
        notify({
          type: 'error',
          title: 'Uninstall failed',
          text: 'Could not uninstall MITK Workbench. Select this message for details.',
          duration: 10_000,
        })
      }
      return { args, open, fail }
    },
    template: `
      <div>
        <VBtn color="error" variant="tonal" class="mr-2" @click="fail">Notify a failure</VBtn>
        <VBtn variant="outlined" @click="open = true">Open the details</VBtn>
        <ErrorDetailsDialog v-bind="args" v-model="open" />
      </div>
    `,
  }),
}

export default meta
type Story = StoryObj<typeof ErrorDetailsDialog>

export const Default: Story = {
  args: {
    title: 'Uninstall failed',
    text: 'Could not uninstall MITK Workbench.',
    error: conflict,
  },
}

export const NoResponse: Story = {
  args: {
    title: 'Could not load the extension list',
    text: 'The extension service did not answer.',
    error: {
      status: null,
      statusText: null,
      method: 'GET',
      url: '/kube-helm-api/extensions',
      detail: null,
      requestId: null,
      message: 'timeout of 10000ms exceeded',
    },
  },
}
