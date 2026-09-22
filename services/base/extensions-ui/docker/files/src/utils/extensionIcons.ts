import { kaapanaIcons } from '@kaapana/base-ui'

// Platform-wide actions use the shared icon map from base-ui.
export { kaapanaIcons }

// Icons for this view's own vocabulary.
export const extensionIcons = {
  workflow: 'mdi-gamepad-variant',
  application: 'mdi-application-outline',
  experimental: 'mdi-test-tube',
  stable: 'mdi-check-decagram',
  filter: 'mdi-filter',
} as const
