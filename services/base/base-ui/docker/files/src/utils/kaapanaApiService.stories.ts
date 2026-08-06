import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { defineComponent, h } from 'vue'
import kaapanaApiService from './kaapanaApiService'

// Surface listing only — calling the wrappers would hit the platform.
const KaapanaApiServiceDemo = defineComponent({
  name: 'KaapanaApiServiceDemo',
  setup() {
    return () =>
      h('ul', Object.keys(kaapanaApiService).map((name) => h('li', h('code', `${name}()`))))
  },
})

const meta: Meta<typeof KaapanaApiServiceDemo> = {
  title: 'kaapanaApiService',
  component: KaapanaApiServiceDemo,
}

export default meta
type Story = StoryObj<typeof KaapanaApiServiceDemo>

export const Default: Story = {}
