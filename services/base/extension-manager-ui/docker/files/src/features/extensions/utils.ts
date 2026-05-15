import type { ExtensionStatus } from '@/shared/types/apiSchemas'

export const extensionStatusColor: Record<ExtensionStatus, string> = {
  pending: 'warning',
  pulling: 'warning',
  pulling_failed: 'error',
  installing: 'warning',
  installing_failed: 'error',
  installed: 'success',
  uninstalling: 'warning',
  uninstalled: 'grey',
  uninstalling_failed: 'error',
}
