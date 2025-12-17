export interface JsonSchema {
  type?: string | string[]
  title?: string
  description?: string
  properties?: Record<string, JsonSchema>
  enum?: unknown[]
  items?: JsonSchema
  format?: string
  default?: unknown
  required?: string[]
  minLength?: number
  maxLength?: number
}
