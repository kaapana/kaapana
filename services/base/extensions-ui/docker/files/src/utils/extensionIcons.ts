import { kaapanaIcons } from '@kaapana/base-ui'

// Actions whose meaning is constant across the platform come from the shared
// map — never an 'mdi-*' string at the call site (design guidelines, "Icons").
export { kaapanaIcons }

// Icons for this view's own domain vocabulary. The shared map is deliberately
// not a catalogue of every symbol in use, so these stay local; they are named
// here rather than inline so one edit changes every occurrence.
export const extensionIcons = {
  workflow: 'mdi-gamepad-variant',
  application: 'mdi-application-outline',
  experimental: 'mdi-test-tube',
  stable: 'mdi-check-decagram',
  filter: 'mdi-filter',
  statusDot: 'mdi-circle',
} as const
