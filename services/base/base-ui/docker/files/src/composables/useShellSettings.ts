import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'
import { useTheme } from 'vuetify'
import { KAAPANA_THEME_DARK, KAAPANA_THEME_LIGHT } from '../utils/vuetifyTheme'

// Follow the shell-owned UI settings (same-origin localStorage["settings"]):
// applied at setup and live via the "storage" event the shell's writes fire.
// darkMode switches the Vuetify theme in place; any other change bumps viewKey
// so the caller can remount its view tree. Must run inside a component setup()
// with Vuetify installed.
export function useShellSettings(
  options: { lightTheme?: string; darkTheme?: string } = {},
): { viewKey: Ref<number> } {
  const { lightTheme = KAAPANA_THEME_LIGHT, darkTheme = KAAPANA_THEME_DARK } = options
  const theme = useTheme()
  const viewKey = ref(0)

  function applyShellSettings() {
    try {
      const settings = JSON.parse(localStorage['settings'] || '{}')
      theme.global.name.value = settings.darkMode ? darkTheme : lightTheme
    } catch {
      // keep current theme on malformed settings
    }
  }

  function settingsChangedBeyondDarkMode(oldValue: string | null, newValue: string | null): boolean {
    const strip = (raw: string | null) => {
      try {
        const settings = JSON.parse(raw || '{}')
        delete settings.darkMode
        return JSON.stringify(settings)
      } catch {
        return ''
      }
    }
    return strip(oldValue) !== strip(newValue)
  }

  function onStorage(e: StorageEvent) {
    if (e.key === 'settings') {
      applyShellSettings()
      if (settingsChangedBeyondDarkMode(e.oldValue, e.newValue)) viewKey.value++
    }
  }

  applyShellSettings()
  onMounted(() => window.addEventListener('storage', onStorage))
  onBeforeUnmount(() => window.removeEventListener('storage', onStorage))

  return { viewKey }
}
