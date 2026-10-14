import { defineStore } from 'pinia'
import { notifyFailure } from '@/utils/notifyFailure'
import { settings as defaultSettings } from '@/static/defaultUIConfig'
import { fetchSettings, putSettings, putSettingsItem, type SettingsItem } from '@/api/settings'
import type { Settings, ThemeMode } from '@/types/settings'

// The extracted view containers read localStorage["settings"] synchronously on
// startup, so the shell must seed it (defaults merged with the DB copy) BEFORE
// the first iframe mounts.

const DARK_SCHEME_QUERY = '(prefers-color-scheme: dark)'

function settingsResponseToObject(response: SettingsItem[]): Record<string, unknown> {
  const converted: Record<string, unknown> = {}
  response.forEach((item) => {
    converted[item.key] = item.value
  })
  return converted
}

// The browser's colour scheme, or the default where it cannot be asked (jsdom).
function systemPrefersDark(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return defaultSettings.darkMode
  }
  return window.matchMedia(DARK_SCHEME_QUERY).matches
}

/** The effective dark flag for a theme choice; "system" asks the browser. */
export function resolveDarkMode(mode: ThemeMode): boolean {
  if (mode === 'system') return systemPrefersDark()
  return mode === 'dark'
}

// Settings stored before the theme choice existed carry only `darkMode`. The
// old dialog saved its default `true` on every Save, so `true` is not a choice
// and follows the browser. Only `false` was set on purpose and stays Light.
export function themeModeOf(fromDb: Record<string, unknown>): ThemeMode {
  const mode = fromDb.themeMode
  if (mode === 'system' || mode === 'light' || mode === 'dark') return mode
  if (fromDb.darkMode === false) return 'light'
  return defaultSettings.themeMode
}

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    settings: structuredClone(defaultSettings) as Settings,
    loaded: false,
    followingSystemScheme: false,
  }),
  getters: {
    darkMode(): boolean {
      return !!this.settings.darkMode
    },
    themeMode(): ThemeMode {
      return this.settings.themeMode ?? defaultSettings.themeMode
    },
    devMode(): boolean {
      return !!this.settings.devMode
    },
  },
  actions: {
    async ensureLoaded() {
      if (this.loaded) return
      try {
        const settingsFromDb = settingsResponseToObject(await fetchSettings())
        delete settingsFromDb.workflows
        const merged = Object.assign(
          {},
          structuredClone(defaultSettings) as Settings,
          settingsFromDb,
        ) as Settings
        merged.themeMode = themeModeOf(settingsFromDb)
        merged.darkMode = resolveDarkMode(merged.themeMode)
        this.settings = merged
        localStorage['settings'] = JSON.stringify(this.settings)
      } catch (err) {
        console.error(err)
        this.settings = structuredClone(defaultSettings) as Settings
        this.settings.darkMode = resolveDarkMode(this.settings.themeMode)
        // Keep the seed of an earlier successful boot: overwriting it with the
        // defaults makes the user's settings look reset in every view.
        if (!localStorage['settings']) {
          localStorage['settings'] = JSON.stringify(this.settings)
        }
        notifyFailure(
          'Could not load your settings',
          'Using the default settings; saving now would overwrite the stored ones.',
          err,
        )
      }
      this.loaded = true
      this.followSystemScheme()
    },
    /** Recompute the effective dark flag and hand it to the views. */
    applyThemeMode() {
      this.settings.darkMode = resolveDarkMode(this.themeMode)
      localStorage['settings'] = JSON.stringify(this.settings)
    },
    /**
     * React to the browser's colour scheme while the choice is "system". The
     * change is not stored: the stored choice is "system", and the next boot
     * asks the browser again.
     */
    followSystemScheme() {
      if (this.followingSystemScheme) return
      if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return
      this.followingSystemScheme = true
      window.matchMedia(DARK_SCHEME_QUERY).addEventListener('change', () => {
        if (this.themeMode === 'system') this.applyThemeMode()
      })
    },
    setThemeMode(mode: ThemeMode) {
      this.settings.themeMode = mode
      this.applyThemeMode()
      putSettingsItem({ key: 'themeMode', value: mode }).catch((err) => {
        console.error(err)
        notifyFailure(
          'Could not save the theme',
          'The setting is applied here but was not stored. Please try again.',
          err,
        )
      })
    },
    setDevMode(value: boolean) {
      this.settings.devMode = value
      localStorage['settings'] = JSON.stringify(this.settings)
      putSettingsItem({ key: 'devMode', value }).catch((err) => {
        console.error(err)
        notifyFailure(
          'Could not save dev mode',
          'The setting is applied here but was not stored. Please try again.',
          err,
        )
      })
    },
    /**
     * Persist the full settings object (SettingsDialog save/restore). Applies
     * locally first and resolves false when the store request failed, so the
     * caller can keep its editor open for a retry.
     */
    async saveSettings(settings: Settings): Promise<boolean> {
      // Deep copy: the caller keeps editing its own object (SettingsDialog's
      // local working copy) and must not alias the store state.
      this.settings = JSON.parse(JSON.stringify(settings)) as Settings
      // The theme choice is the source of truth; the flag the views read follows it.
      this.settings.darkMode = resolveDarkMode(this.themeMode)
      // The localStorage write fires a "storage" event in every embedded
      // view, which updates itself — nothing is reloaded.
      localStorage['settings'] = JSON.stringify(this.settings)
      const items: SettingsItem[] = Object.keys(this.settings).map((key) => ({
        key,
        value: this.settings[key],
      }))
      try {
        await putSettings(items)
        return true
      } catch (err) {
        console.error(err)
        notifyFailure(
          'Could not save settings',
          'Your changes are applied here but were not stored. Please try again.',
          err,
        )
        return false
      }
    },
  },
})
