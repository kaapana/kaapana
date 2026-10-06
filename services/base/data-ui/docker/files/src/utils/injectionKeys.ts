import type { InjectionKey } from 'vue'

export const OPEN_SCHEMAS_KEY: InjectionKey<(key?: string) => void> = Symbol('openSchemas')
