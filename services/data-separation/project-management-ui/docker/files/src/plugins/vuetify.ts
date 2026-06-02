/**
 * plugins/vuetify.ts
 *
 * Framework documentation: https://vuetifyjs.com`
 */

// Styles
import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'

// Composables
import { createVuetify } from 'vuetify'
import { vuetifyThemeConfig, vuetifyDefaults } from '@/theme/kaapana-theme'

function readStoredTheme(): 'light' | 'dark' | null {
  // Read-only — the landing page owns writing to localStorage
  try {
    const settings = JSON.parse(localStorage.getItem('settings') || '{}');
    if (settings.darkMode === true) return 'dark';
    if (settings.darkMode === false) return 'light';
  } catch { /* ignore */ }
  return null;
}

function getDefaultTheme(): 'light' | 'dark' {
  // Stored preference always wins — never overwrite it
  const stored = readStoredTheme();
  if (stored) return stored;

  // No preference stored yet — follow the OS
  return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

// Create the vuetify instance
const vuetify = createVuetify({
  theme: {
    defaultTheme: getDefaultTheme(),
    ...vuetifyThemeConfig,
  },
  defaults: vuetifyDefaults,
});

// Landing page changed settings.darkMode in another tab → sync here
window.addEventListener('storage', (event) => {
  if (event.key === 'settings') {
    const stored = readStoredTheme();
    if (stored) vuetify.theme.global.name.value = stored;
  }
});

// OS theme change — only follow if no explicit preference is stored
if (window.matchMedia) {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (!readStoredTheme()) {
      vuetify.theme.global.name.value = e.matches ? 'dark' : 'light';
    }
  });
}

// https://vuetifyjs.com/en/introduction/why-vuetify/#feature-guides
export default vuetify;
