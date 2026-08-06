import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { defineComponent, h } from 'vue'
import { httpClient, httpClientWithoutTimeout } from './httpClient'

// The scoping interceptor is a no-op here — the story URL is unscoped.
const HttpClientDemo = defineComponent({
  name: 'HttpClientDemo',
  setup() {
    return () =>
      h('dl', [
        h('dt', 'httpClient.defaults.timeout'),
        h('dd', h('code', String(httpClient.defaults.timeout))),
        h('dt', 'httpClientWithoutTimeout.defaults.timeout'),
        h('dd', h('code', String(httpClientWithoutTimeout.defaults.timeout))),
      ])
  },
})

const meta: Meta<typeof HttpClientDemo> = {
  title: 'httpClient',
  component: HttpClientDemo,
}

export default meta
type Story = StoryObj<typeof HttpClientDemo>

export const Default: Story = {}
