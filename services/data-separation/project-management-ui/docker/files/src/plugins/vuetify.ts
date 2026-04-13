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

// Function to get theme preference
function getDefaultTheme(): 'light' | 'dark' {
  // First, try to read from browser's prefers-color-scheme
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
    return 'light';
  }
  
  // Second, try to read from localStorage (set by landing page)
  try {
    const settingsStr = localStorage.getItem('settings');
    if (settingsStr) {
      const settings = JSON.parse(settingsStr);
      if (settings.darkMode === false) {
        return 'light';
      }
    }
  } catch (e) {
    // Ignore parse errors
  }
  
  // Default to dark
  return 'dark';
}

// Create the vuetify instance
const vuetify = createVuetify({
  theme: {
    defaultTheme: getDefaultTheme(),
  },
});

// Listen for localStorage changes (from other tabs/windows)
window.addEventListener('storage', (event) => {
  if (event.key === 'settings') {
    const newTheme = getDefaultTheme();
    vuetify.theme.global.name.value = newTheme;
  }
});

// Also listen for browser theme changes
if (window.matchMedia) {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    const newTheme = e.matches ? 'dark' : 'light';
    vuetify.theme.global.name.value = newTheme;
  });
}

// https://vuetifyjs.com/en/introduction/why-vuetify/#feature-guides
export default vuetify;
