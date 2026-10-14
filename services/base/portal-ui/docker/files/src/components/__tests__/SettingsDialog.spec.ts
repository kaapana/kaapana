import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import SettingsDialog from '@/components/SettingsDialog.vue'

vi.mock('@/api/settings', () => ({
  fetchSettings: vi.fn().mockResolvedValue([]),
  putSettings: vi.fn().mockResolvedValue(undefined),
  putSettingsItem: vi.fn().mockResolvedValue(undefined),
  loadDicomTagMapping: vi.fn().mockResolvedValue({}),
}))

// Regression: a setup throw (structuredClone DataCloneError on the reactive
// store proxy) unmounts the whole component, so the activator button
// disappeared.
describe('SettingsDialog', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  function mountDialog() {
    return mount(SettingsDialog, {
      global: {
        plugins: [createVuetify({ components, directives })],
      },
    })
  }

  it('renders its activator button (store state is a reactive proxy)', () => {
    const wrapper = mountDialog()
    expect(wrapper.find('button[title="Settings"]').exists()).toBe(true)
  })
})
