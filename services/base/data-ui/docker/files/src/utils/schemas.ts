import { isAxiosError } from 'axios'
import { reactive } from 'vue'
import { fetchMetadataSchemaRecord, listMetadataSchemas } from '@/services/api'
import type { JsonSchema } from '@/types/jsonSchema'

export const PERMISSIONS_KEY = 'permissions'

type SchemaState =
  | { status: 'loading' }
  | { status: 'missing' }
  | { status: 'error'; error: unknown }
  | { status: 'loaded'; schema: JsonSchema }

const cache = reactive<Record<string, SchemaState>>({})

export function schemaState(key: string): SchemaState | undefined {
  return cache[key]
}

export async function loadSchema(key: string, force = false): Promise<void> {
  const current = cache[key]
  if (!force && current && current.status !== 'error') {
    return
  }
  cache[key] = { status: 'loading' }
  try {
    const record = await fetchMetadataSchemaRecord(key)
    cache[key] = { status: 'loaded', schema: record.schema as JsonSchema }
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === 400) {
      cache[key] = { status: 'missing' }
    } else {
      cache[key] = { status: 'error', error }
    }
  }
}

export function renderableSchema(key: string): JsonSchema | null {
  const state = cache[key]
  if (state?.status !== 'loaded') {
    return null
  }
  const schema = state.schema
  const type = Array.isArray(schema.type) ? schema.type[0] : schema.type
  if (type && type !== 'object') {
    return null
  }
  return Object.keys(schema.properties ?? {}).length ? schema : null
}

export function forgetSchema(key: string) {
  delete cache[key]
}

export { listMetadataSchemas }
