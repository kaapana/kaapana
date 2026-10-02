import { kaapanaIcons } from '@kaapana/base-ui'

export { kaapanaIcons }

export const federationIcons = {
  local: 'mdi-home',
  remote: 'mdi-cloud-braces',
  copy: 'mdi-content-copy',
  enabled: kaapanaIcons.success,
  disabled: 'mdi-minus-circle-outline',
} as const
