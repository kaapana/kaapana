import axios from 'axios'

export interface MinioDocument {
  bucket: string
  path: string
  extension: string
  modification_time: string
  creation_time: string
  size: number
}

export interface DocumentEntry {
  file_id: string
  file: MinioDocument
  favicon: string | null
  app_name: string
  action_name: string
  url: string
}

export async function fetchDocuments(): Promise<DocumentEntry[]> {
  const { data } = await axios.get<DocumentEntry[]>('documents/')
  return data
}

export async function rescanDocuments(): Promise<void> {
  await axios.post('documents/refresh')
}

export function documentUpdatesUrl(): string {
  const url = new URL('ws', window.location.href)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.search = ''
  url.hash = ''
  return url.toString()
}
