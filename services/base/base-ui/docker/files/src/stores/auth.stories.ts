import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { defineComponent, h } from 'vue'
import { useAuthStore } from './auth'

// Initial (logged-out) state only — checkAuth() would hit the auth proxy.
const AuthStoreDemo = defineComponent({
  name: 'AuthStoreDemo',
  setup() {
    const auth = useAuthStore()
    return () =>
      h('dl', [
        h('dt', 'isAuthenticated'),
        h('dd', h('code', JSON.stringify(auth.isAuthenticated))),
        h('dt', 'currentUser'),
        h('dd', h('code', JSON.stringify(auth.currentUser))),
      ])
  },
})

const meta: Meta<typeof AuthStoreDemo> = {
  title: 'stores/auth',
  component: AuthStoreDemo,
}

export default meta
type Story = StoryObj<typeof AuthStoreDemo>

export const Default: Story = {}
