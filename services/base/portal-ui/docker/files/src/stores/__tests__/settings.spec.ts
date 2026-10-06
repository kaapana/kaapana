import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/api/settings', () => ({
  fetchSettings: vi.fn(),
  putSettings: vi.fn(),
  putSettingsItem: vi.fn(),
}))
vi.mock('@/utils/notifyFailure', () => ({ notifyFailure: vi.fn() }))

import { fetchSettings, putSettingsItem } from '@/api/settings'
import { useSettingsStore } from '@/stores/settings'

// A controllable stand-in for window.matchMedia, which jsdom does not have.
function fakeSystemScheme(initialDark: boolean) {
  const listeners: Array<() => void> = []
  const mql = {
    matches: initialDark,
    media: '(prefers-color-scheme: dark)',
    addEventListener: (_type: string, cb: () => void) => listeners.push(cb),
    removeEventListener: vi.fn(),
  }
  Object.defineProperty(window, 'matchMedia', { configurable: true, value: () => mql })
  return {
    setDark(dark: boolean) {
      mql.matches = dark
      listeners.forEach((cb) => cb())
    },
  }
}

describe('settings store theme choice', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.mocked(putSettingsItem).mockReset().mockResolvedValue(undefined)
  })

  afterEach(() => {
    Reflect.deleteProperty(window, 'matchMedia')
  })

  it('follows the browser when nothing is stored, and keeps following it live', async () => {
    const system = fakeSystemScheme(true)
    vi.mocked(fetchSettings).mockResolvedValue([])
    const store = useSettingsStore()
    await store.ensureLoaded()
    expect(store.themeMode).toBe('system')
    expect(store.darkMode).toBe(true)

    system.setDark(false)
    expect(store.darkMode).toBe(false)
    // The views get the new flag; the stored choice stays "system".
    expect(JSON.parse(localStorage['settings'])).toMatchObject({
      themeMode: 'system',
      darkMode: false,
    })
    expect(putSettingsItem).not.toHaveBeenCalled()
  })

  it('keeps a darkMode:false stored before the choice existed as a fixed light theme', async () => {
    fakeSystemScheme(true)
    vi.mocked(fetchSettings).mockResolvedValue([{ key: 'darkMode', value: false }])
    const store = useSettingsStore()
    await store.ensureLoaded()
    expect(store.themeMode).toBe('light')
    expect(store.darkMode).toBe(false)
  })

  // The old dialog stored the default darkMode:true on every Save, so it is
  // not a choice and must not pin the user to the dark theme.
  it('follows the browser for a darkMode:true stored before the choice existed', async () => {
    fakeSystemScheme(false)
    vi.mocked(fetchSettings).mockResolvedValue([{ key: 'darkMode', value: true }])
    const store = useSettingsStore()
    await store.ensureLoaded()
    expect(store.themeMode).toBe('system')
    expect(store.darkMode).toBe(false)
  })

  it('a stored choice wins over the browser and ignores its changes', async () => {
    const system = fakeSystemScheme(false)
    vi.mocked(fetchSettings).mockResolvedValue([
      { key: 'themeMode', value: 'dark' },
      { key: 'darkMode', value: false },
    ])
    const store = useSettingsStore()
    await store.ensureLoaded()
    expect(store.darkMode).toBe(true)

    system.setDark(true)
    system.setDark(false)
    expect(store.darkMode).toBe(true)
  })

  it('setThemeMode applies at once, seeds the views and stores one item', async () => {
    fakeSystemScheme(true)
    vi.mocked(fetchSettings).mockResolvedValue([])
    const store = useSettingsStore()
    await store.ensureLoaded()

    store.setThemeMode('light')

    expect(store.darkMode).toBe(false)
    expect(JSON.parse(localStorage['settings'])).toMatchObject({
      themeMode: 'light',
      darkMode: false,
    })
    expect(putSettingsItem).toHaveBeenCalledWith({ key: 'themeMode', value: 'light' })
  })

  it('saveSettings derives the flag the views read from the saved choice', async () => {
    fakeSystemScheme(false)
    vi.mocked(fetchSettings).mockResolvedValue([])
    const store = useSettingsStore()
    await store.ensureLoaded()

    // A working copy that still carries a stale flag next to the choice.
    await store.saveSettings({ ...store.settings, themeMode: 'dark', darkMode: false })

    expect(store.darkMode).toBe(true)
    expect(JSON.parse(localStorage['settings']).darkMode).toBe(true)
  })
})
