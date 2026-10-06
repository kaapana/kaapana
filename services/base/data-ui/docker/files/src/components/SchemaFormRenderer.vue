<script setup lang="ts">
import { computed } from 'vue'
import type { JsonSchema } from '@/types/jsonSchema'

defineOptions({
  name: 'SchemaFormRenderer',
})

const props = defineProps<{
  schema: JsonSchema
  modelValue: unknown
  name?: string
  required?: boolean
  disabled?: boolean
  level?: number
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: unknown): void
}>()

const level = computed(() => props.level ?? 0)

const normalizedType = computed(() => {
  const { type } = props.schema
  if (Array.isArray(type)) {
    return type[0] ?? null
  }
  return type ?? null
})

const label = computed(() => props.schema.title ?? props.name ?? 'Value')

const isEnumField = computed(() => Array.isArray(props.schema.enum) && props.schema.enum.length > 0)
const enumOptions = computed(() => (Array.isArray(props.schema.enum) ? props.schema.enum : []))

const useTextarea = computed(() => {
  if (normalizedType.value !== 'string') {
    return false
  }
  if (props.schema.format === 'multiline') {
    return true
  }
  if (typeof props.schema.maxLength === 'number') {
    return props.schema.maxLength > 200
  }
  return false
})

const objectValue = computed<Record<string, unknown>>(() => {
  if (
    props.modelValue &&
    typeof props.modelValue === 'object' &&
    !Array.isArray(props.modelValue)
  ) {
    return props.modelValue as Record<string, unknown>
  }
  return {}
})

const childProperties = computed(() => props.schema.properties ?? {})
const requiredKeys = computed(() => new Set(props.schema.required ?? []))

function updateChildValue(key: string, childValue: unknown) {
  const next = { ...objectValue.value }
  if (
    childValue === undefined ||
    childValue === null ||
    (typeof childValue === 'object' &&
      childValue !== null &&
      !Object.keys(childValue as Record<string, unknown>).length)
  ) {
    delete next[key]
  } else {
    next[key] = childValue
  }
  emit('update:modelValue', next)
}

const stringValue = computed({
  get: () => {
    if (props.modelValue == null) {
      return ''
    }
    return String(props.modelValue)
  },
  set: (value: string | null) => {
    emit('update:modelValue', value ? value : undefined)
  },
})

function handleStringSelect(value: string | null) {
  emit('update:modelValue', value ?? undefined)
}

const numberValue = computed(() => {
  if (typeof props.modelValue === 'number') {
    return props.modelValue
  }
  return props.modelValue == null ? null : Number(props.modelValue)
})

function handleNumberInput(value: string) {
  if (!value) {
    emit('update:modelValue', undefined)
    return
  }
  const parsed = Number(value)
  if (!Number.isNaN(parsed)) {
    emit('update:modelValue', parsed)
  }
}

const booleanValue = computed({
  get: () => {
    if (typeof props.modelValue === 'boolean') {
      return props.modelValue
    }
    return Boolean(props.modelValue)
  },
  set: (value: boolean) => {
    emit('update:modelValue', value)
  },
})

const fallbackJson = computed(() => {
  if (props.modelValue === undefined) {
    return ''
  }
  try {
    return JSON.stringify(props.modelValue, null, 2)
  } catch {
    return String(props.modelValue)
  }
})

const rules = computed(() =>
  props.required
    ? [
        (value: unknown) =>
          (value !== null && value !== undefined && String(value).trim() !== '') ||
          `Enter ${label.value}; the field is required.`,
      ]
    : [],
)

const numberRules = computed(() => [
  ...rules.value,
  (value: unknown) =>
    value === null ||
    value === undefined ||
    value === '' ||
    normalizedType.value !== 'integer' ||
    Number.isInteger(Number(value)) ||
    'Enter a whole number.',
])

function hasSupportedChildren(): boolean {
  return Object.keys(childProperties.value).length > 0
}
</script>

<template>
  <div class="schema-field" :class="{ 'schema-nested': level > 1 }">
    <template v-if="normalizedType === 'object' && hasSupportedChildren()">
      <div v-if="level > 0" class="mb-2">
        <div class="text-subtitle-2">{{ label }}</div>
        <div v-if="schema.description" class="text-caption text-medium-emphasis">
          {{ schema.description }}
        </div>
      </div>
      <SchemaFormRenderer
        v-for="(childSchema, key) in childProperties"
        :key="`${level}-${key}`"
        :schema="childSchema"
        :name="childSchema.title ?? key"
        :required="requiredKeys.has(key)"
        :disabled="disabled"
        :level="level + 1"
        :model-value="objectValue[key]"
        @update:model-value="(val) => updateChildValue(key, val)"
      />
    </template>
    <template v-else-if="normalizedType === 'string'">
      <v-select
        v-if="isEnumField"
        :label="label"
        :items="enumOptions"
        :model-value="stringValue || null"
        :disabled="disabled"
        :rules="rules"
        :hint="schema.description"
        :persistent-hint="Boolean(schema.description)"
        clearable
        @update:model-value="handleStringSelect"
      />
      <v-textarea
        v-else-if="useTextarea"
        v-model="stringValue"
        :label="label"
        :disabled="disabled"
        :rules="rules"
        :hint="schema.description"
        :persistent-hint="Boolean(schema.description)"
        rows="3"
        max-rows="6"
        auto-grow
      />
      <v-text-field
        v-else
        v-model="stringValue"
        :label="label"
        :disabled="disabled"
        :rules="rules"
        :hint="schema.description"
        :persistent-hint="Boolean(schema.description)"
      />
    </template>
    <v-text-field
      v-else-if="normalizedType === 'number' || normalizedType === 'integer'"
      :label="label"
      :disabled="disabled"
      :rules="numberRules"
      :hint="schema.description"
      :persistent-hint="Boolean(schema.description)"
      type="number"
      :model-value="numberValue ?? ''"
      @update:model-value="handleNumberInput"
    />
    <v-switch
      v-else-if="normalizedType === 'boolean'"
      v-model="booleanValue"
      :label="label"
      :disabled="disabled"
      :hint="schema.description"
      :persistent-hint="Boolean(schema.description)"
      color="primary"
      inset
    />
    <v-textarea
      v-else
      :model-value="fallbackJson"
      :label="label"
      rows="3"
      readonly
      hint="This field type cannot be edited in the form. Edit the entry as JSON instead."
      persistent-hint
    />
  </div>
</template>

<style scoped>
.schema-field {
  margin-bottom: 8px;
}

.schema-nested {
  padding-left: 16px;
  border-left: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
