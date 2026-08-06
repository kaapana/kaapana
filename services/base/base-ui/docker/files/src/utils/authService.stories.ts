import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { defineComponent, h } from 'vue'
import AuthService from './authService'

// Surface listing only — getToken()/logout() are not safe to call in a story.
const AuthServiceDemo = defineComponent({
  name: 'AuthServiceDemo',
  setup() {
    return () =>
      h('ul', Object.keys(AuthService).map((name) => h('li', h('code', `AuthService.${name}()`))))
  },
})

const meta: Meta<typeof AuthServiceDemo> = {
  title: 'authService',
  component: AuthServiceDemo,
}

export default meta
type Story = StoryObj<typeof AuthServiceDemo>

export const Default: Story = {}
