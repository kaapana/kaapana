import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { defineComponent, h, onBeforeUnmount, ref } from 'vue'
import { VSwitch } from 'vuetify/components'
import { postViewDirty } from './viewDirty'

// The story window is its own parent, so the listener below echoes the
// kaapana:view-dirty messages the portal-ui shell would receive.
const ViewDirtyDemo = defineComponent({
  name: 'ViewDirtyDemo',
  setup() {
    const dirty = ref(false)
    const received = ref('(nothing yet)')
    const onMessage = (event: MessageEvent) => {
      if (event.data?.type === 'kaapana:view-dirty') received.value = JSON.stringify(event.data)
    }
    window.addEventListener('message', onMessage)
    onBeforeUnmount(() => window.removeEventListener('message', onMessage))
    return () =>
      h('div', [
        h(VSwitch, {
          label: 'View has unsaved state',
          modelValue: dirty.value,
          'onUpdate:modelValue': (value: boolean | null) => {
            dirty.value = !!value
            postViewDirty(dirty.value)
          },
        }),
        h('code', `shell received: ${received.value}`),
      ])
  },
})

const meta: Meta<typeof ViewDirtyDemo> = {
  title: 'postViewDirty',
  component: ViewDirtyDemo,
}

export default meta
type Story = StoryObj<typeof ViewDirtyDemo>

export const Default: Story = {}
