import { defineStore } from 'pinia'
import { notify } from '@kyvg/vue3-notification'
import { settings as defaultSettings } from '@/static/defaultUIConfig'
import { fetchSettings, putSettings, putSettingsItem, type SettingsItem } from '@/api/settings'
import type { Settings } from '@/types/settings'

// The extracted view containers read localStorage["settings"] synchronously on
// startup, so the shell must seed it (defaults merged with the DB copy) BEFORE
// the first iframe mounts.

function settingsResponseToObject(response: SettingsItem[]): Record<string, unknown> {
  const converted: Record<string, unknown> = {}
  response.forEach((item) => {
    converted[item.key] = item.value
  })
  return converted
}

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    settings: structuredClone(defaultSettings) as Settings,
    loaded: false,
  }),
  getters: {
    darkMode(): boolean {
      return !!this.settings.darkMode
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
        this.settings = Object.assign(
          {},
          structuredClone(defaultSettings) as Settings,
          settingsFromDb,
        )
        localStorage['settings'] = JSON.stringify(this.settings)
      } catch (err) {
        console.log(err)
        this.settings = structuredClone(defaultSettings) as Settings
        // Keep the seed of an earlier successful boot: overwriting it with the
        // defaults makes the user's settings look reset in every view.
        if (!localStorage['settings']) {
          localStorage['settings'] = JSON.stringify(this.settings)
        }
        notify({
          type: 'error',
          title: 'Could not load your settings',
          text: 'Using the default settings; saving now would overwrite the stored ones.',
        })
      }
      this.loaded = true
    },
    setDarkMode(value: boolean) {
      this.settings.darkMode = value
      localStorage['settings'] = JSON.stringify(this.settings)
      putSettingsItem({ key: 'darkMode', value }).catch((err) => {
        console.log(err)
        notify({
          type: 'error',
          title: 'Could not save dark mode',
          text: 'The setting is applied here but was not stored. Please try again.',
        })
      })
    },
    setDevMode(value: boolean) {
      this.settings.devMode = value
      localStorage['settings'] = JSON.stringify(this.settings)
      putSettingsItem({ key: 'devMode', value }).catch((err) => {
        console.log(err)
        notify({
          type: 'error',
          title: 'Could not save dev mode',
          text: 'The setting is applied here but was not stored. Please try again.',
        })
      })
    },
    /** Persist the full settings object (SettingsDialog save/restore). */
    async saveSettings(settings: Settings) {
      // Deep copy: the caller keeps editing its own object (SettingsDialog's
      // local working copy) and must not alias the store state.
      this.settings = JSON.parse(JSON.stringify(settings)) as Settings
      // The localStorage write fires a "storage" event in every embedded
      // view, which updates itself — nothing is reloaded.
      localStorage['settings'] = JSON.stringify(this.settings)
      const items: SettingsItem[] = Object.keys(settings).map((key) => ({
        key,
        value: settings[key],
      }))
      try {
        await putSettings(items)
      } catch (err) {
        console.log(err)
        notify({
          type: 'error',
          title: 'Could not save settings',
          text: 'Your changes are applied here but were not stored. Please try again.',
        })
      }
    },
  },
})
