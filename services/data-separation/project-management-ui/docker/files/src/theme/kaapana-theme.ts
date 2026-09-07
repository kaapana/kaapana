/**
 * Kaapana design tokens — single source of truth for colors and defaults.
 *
 * TO USE IN any micro-frontend (Vue 3 / Vuetify 3):
 *   import { vuetifyThemeConfig } from './kaapana-theme'
 *   createVuetify({ theme: vuetifyThemeConfig })
 *
 * CSS custom properties version (for non-Vuetify apps):
 *   --kaapana-primary:     #005BA0
 *   --kaapana-primary-dark:#1E88E5
 *   --kaapana-secondary:   #5A696E
 *   --kaapana-error:       #C62828
 *   --kaapana-warning:     #EF6C00
 *   --kaapana-success:     #2E7D32
 */

// ── Vuetify 3 (project-management-ui and future micro-frontends) ────────────
export const vuetifyThemeConfig = {
  themes: {
    light: {
      dark: false,
      colors: {
        primary:   '#005BA0',
        secondary: '#5A696E',
        error:     '#C62828',
        warning:   '#EF6C00',
        success:   '#2E7D32',
        info:      '#0277BD',
      },
    },
    dark: {
      dark: true,
      colors: {
        primary:   '#1E88E5',
        secondary: '#78909C',
        error:     '#EF5350',
        warning:   '#FFA726',
        success:   '#66BB6A',
        info:      '#29B6F6',
      },
    },
  },
};

// ── Global Vuetify 3 component defaults ────────────────────────────────────
export const vuetifyDefaults = {
  VCard:       { rounded: 'lg', elevation: 0 },
  VSheet:      { rounded: 'lg' },
  VDialog:     { VCard: { rounded: 'lg', elevation: 0 } },
  VTable:      { hover: true },
  VDataTable:  { hover: true },
  VTextField:  { variant: 'outlined', density: 'compact' },
  VSelect:     { variant: 'outlined', density: 'compact' },
  VAlert:      { rounded: 'lg' },
  VChip:       { rounded: 'lg' },
  VSnackbar:   { rounded: 'lg' },
};