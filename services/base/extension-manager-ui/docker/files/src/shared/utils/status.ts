import type { ContentStatus, ExtensionStatus } from '@/shared/types/apiSchemas'

export type StatusTone = 'success' | 'error' | 'progress' | 'neutral'

export interface StatusPresentation {
  label: string
  tone: StatusTone
}

export const extensionStatus: Record<ExtensionStatus, StatusPresentation> = {
  pending: { label: 'Waiting to install', tone: 'progress' },
  pulling: { label: 'Downloading', tone: 'progress' },
  pulling_failed: { label: 'Download failed', tone: 'error' },
  installing: { label: 'Installing', tone: 'progress' },
  installing_failed: { label: 'Installation failed', tone: 'error' },
  installed: { label: 'Installed', tone: 'success' },
  uninstalling: { label: 'Uninstalling', tone: 'progress' },
  uninstalled: { label: 'Uninstalled', tone: 'neutral' },
  uninstalling_failed: { label: 'Uninstall failed', tone: 'error' },
}

export const contentStatus: Record<ContentStatus, StatusPresentation> = {
  pending: { label: 'Waiting', tone: 'progress' },
  installing: { label: 'Installing', tone: 'progress' },
  installation_failed: { label: 'Installation failed', tone: 'error' },
  installed: { label: 'Installed', tone: 'success' },
  uninstalling: { label: 'Uninstalling', tone: 'progress' },
  uninstallation_failed: { label: 'Uninstall failed', tone: 'error' },
  uninstalled: { label: 'Uninstalled', tone: 'neutral' },
}

export function presentExtensionStatus(status: string): StatusPresentation {
  return extensionStatus[status as ExtensionStatus] ?? { label: status, tone: 'neutral' }
}

export function presentContentStatus(status: string): StatusPresentation {
  return contentStatus[status as ContentStatus] ?? { label: status, tone: 'neutral' }
}

export const UNINSTALLABLE_STATUSES: readonly ExtensionStatus[] = [
  'installed',
  'pulling_failed',
  'installing_failed',
  'uninstalling_failed',
]

export const RETRYABLE_INSTALL_STATUSES: readonly ExtensionStatus[] = [
  'pulling_failed',
  'installing_failed',
]

export function isTransitional(status: string): boolean {
  return presentExtensionStatus(status).tone === 'progress'
}

export function isChanging(status: string): boolean {
  return isTransitional(status) || status === 'uninstalled'
}

export function plural(count: number, singular: string, pluralForm = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : pluralForm}`
}
