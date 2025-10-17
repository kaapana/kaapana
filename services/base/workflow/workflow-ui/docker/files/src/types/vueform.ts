// Vueform schema types for type-safe form building

export interface VueformFieldBase {
  type: string
  label?: string
  description?: string
  descriptionPosition?: 'before' | 'after'
  default?: any
  rules?: string
  placeholder?: string
}

export interface VueformTextField extends VueformFieldBase {
  type: 'text'
  default?: string
}

export interface VueformNumberField extends VueformFieldBase {
  type: 'number'
  default?: number
  min?: number
  max?: number
  step?: number
}

export interface VueformToggleField extends VueformFieldBase {
  type: 'toggle'
  default?: boolean
}

export interface VueformSelectField extends VueformFieldBase {
  type: 'select'
  items: string[]
  default?: string
}

export interface VueformMultiselectField extends VueformFieldBase {
  type: 'multiselect'
  items: string[]
  default?: string[]
  mode?: 'tags' | 'multiple'
  closeOnSelect?: boolean
  searchable?: boolean
  canClear?: boolean
  hideSelected?: boolean
  object?: boolean
}

export interface VueformTextareaField extends VueformFieldBase {
  type: 'textarea'
  rows?: number
  default?: string
}

export interface VueformDateField extends VueformFieldBase {
  type: 'date' | 'datetime'
  default?: string
}

export interface VueformFileField extends VueformFieldBase {
  type: 'file'
}

export interface VueformStaticField {
  type: 'static'
  content: string
}

export type VueformField = 
  | VueformTextField 
  | VueformNumberField 
  | VueformToggleField 
  | VueformSelectField 
  | VueformMultiselectField 
  | VueformTextareaField 
  | VueformDateField 
  | VueformFileField
  | VueformStaticField

export type VueformSchema = Record<string, VueformField>
