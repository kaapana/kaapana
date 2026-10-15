import type { DocumentEntry } from '@/api/documents'

export type SortKey = 'name' | 'modified'

export interface FolderRow {
  kind: 'folder'
  name: string
  path: string[]
  modified: string
  count: number
}

export interface FileRow {
  kind: 'file'
  name: string
  modified: string
  size: number
  doc: DocumentEntry
}

export type Row = FolderRow | FileRow

export function segments(path: string): string[] {
  return path.split('/').filter(Boolean)
}

function isInside(parts: string[], folder: string[]): boolean {
  return parts.length > folder.length && folder.every((name, i) => parts[i] === name)
}

export function folderExists(documents: DocumentEntry[], folder: string[]): boolean {
  return folder.length === 0 || documents.some((doc) => isInside(segments(doc.file.path), folder))
}

export function closestFolder(documents: DocumentEntry[], folder: string[]): string[] {
  let candidate = folder
  while (!folderExists(documents, candidate)) candidate = candidate.slice(0, -1)
  return candidate
}

export function folderRows(documents: DocumentEntry[], folder: string[]): Row[] {
  const folders = new Map<string, FolderRow>()
  const files: FileRow[] = []
  for (const doc of documents) {
    const parts = segments(doc.file.path)
    if (!isInside(parts, folder)) continue
    const name = parts[folder.length]
    if (parts.length === folder.length + 1) {
      files.push(fileRow(doc, name))
      continue
    }
    const existing = folders.get(name)
    if (existing) {
      existing.count += 1
      if (doc.file.modification_time > existing.modified)
        existing.modified = doc.file.modification_time
    } else {
      folders.set(name, {
        kind: 'folder',
        name,
        path: [...folder, name],
        modified: doc.file.modification_time,
        count: 1,
      })
    }
  }
  return [...folders.values(), ...files]
}

export function searchRows(documents: DocumentEntry[], needle: string): FileRow[] {
  const query = needle.toLowerCase()
  return documents
    .filter((doc) => doc.file.path.toLowerCase().includes(query))
    .map((doc) => fileRow(doc, segments(doc.file.path).join('/')))
}

function fileRow(doc: DocumentEntry, name: string): FileRow {
  return { kind: 'file', name, modified: doc.file.modification_time, size: doc.file.size, doc }
}

export function sortRows<T extends Row>(rows: T[], key: SortKey): T[] {
  const byKey = (a: Row, b: Row) =>
    key === 'name'
      ? a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' })
      : b.modified.localeCompare(a.modified)
  return [...rows].sort((a, b) => (a.kind === b.kind ? byKey(a, b) : a.kind === 'folder' ? -1 : 1))
}

const sizeUnits = ['B', 'KB', 'MB', 'GB', 'TB']

export function formatSize(bytes: number): string {
  let value = bytes
  let unit = 0
  while (value >= 1024 && unit < sizeUnits.length - 1) {
    value /= 1024
    unit += 1
  }
  const digits = unit === 0 || value >= 10 ? 0 : 1
  return `${value.toFixed(digits)} ${sizeUnits[unit]}`
}
