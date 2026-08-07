import http from '@/api/http'

export interface SettingsItem {
  key: string
  value: unknown
}

export async function fetchSettings(): Promise<SettingsItem[]> {
  const res = await http.get<SettingsItem[]>('/kaapana-backend/settings')
  return res.data
}

export async function putSettingsItem(item: SettingsItem): Promise<void> {
  await http.put('/kaapana-backend/settings/item', item)
}

export async function putSettings(items: SettingsItem[]): Promise<void> {
  await http.put('/kaapana-backend/settings', items)
}

/** Mapping of human-readable DICOM tag names to opensearch field names. */
export async function loadDicomTagMapping(): Promise<Record<string, string>> {
  const res = await http.get<Record<string, string>>('/kaapana-backend/dataset/fields')
  return res.data
}
