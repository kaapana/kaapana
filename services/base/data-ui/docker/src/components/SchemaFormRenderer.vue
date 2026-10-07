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
  if (props.modelValue && typeof props.modelValue === 'object' && !Array.isArray(props.modelValue)) {
    return props.modelValue as Record<string, unknown>
  }
  return {}
})

const childProperties = computed(() => props.schema.properties ?? {})
const requiredKeys = computed(() => new Set(props.schema.required ?? []))

function updateChildValue(key: string, childValue: unknown) {
  const next = { ...objectValue.value }
  if (childValue === undefined || childValue === null || (typeof childValue === 'object' && childValue !== null && !Object.keys(childValue as Record<string, unknown>).length)) {
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
  set: (value: string) => {
    emit('update:modelValue', value)
  },
})

function handleStringSelect(value: string | null) {
  emit('update:modelValue', value ?? '')
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
  } catch (error) {
    return String(props.modelValue)
  }
})

function hasSupportedChildren(): boolean {
  return Object.keys(childProperties.value).length > 0
}
</script>

<template>
  <div class="schema-field" :class="[`schema-level-${level}`]">
    <template v-if="normalizedType === 'object' && hasSupportedChildren()">
      <div class="schema-object-header" v-if="label">
        <div class="schema-label">
          {{ label }}
          <span v-if="required" class="schema-required">*</span>
        </div>
        <div v-if="schema.description" class="schema-description">{{ schema.description }}</div>
      </div>
      <div class="schema-object-body">
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
      </div>
    </template>
    <template v-else-if="normalizedType === 'string'">
      <v-select
        v-if="isEnumField"
        :label="label"
        :items="enumOptions"
        :model-value="stringValue"
        :disabled="disabled"
        :required="required"
        variant="outlined"
        density="compact"
        @update:model-value="handleStringSelect"
      ></v-select>
      <v-textarea
        v-else-if="useTextarea"
        v-model="stringValue"
        :label="label"
        :disabled="disabled"
        :required="required"
        variant="outlined"
        rows="3"
        max-rows="6"
        density="compact"
        auto-grow
      ></v-textarea>
      <v-text-field
        v-else
        v-model="stringValue"
        :label="label"
        :disabled="disabled"
        :required="required"
        variant="outlined"
        density="compact"
      ></v-text-field>
      <div v-if="schema.description" class="schema-description">{{ schema.description }}</div>
    </template>
    <template v-else-if="normalizedType === 'number' || normalizedType === 'integer'">
      <v-text-field
        :label="label"
        :disabled="disabled"
        :required="required"
        variant="outlined"
        density="compact"
        type="number"
        :model-value="numberValue ?? ''"
        @update:model-value="handleNumberInput"
      ></v-text-field>
      <div v-if="schema.description" class="schema-description">{{ schema.description }}</div>
    </template>
    <template v-else-if="normalizedType === 'boolean'">
      <v-switch
        v-model="booleanValue"
        :label="label"
        :disabled="disabled"
        inset
      ></v-switch>
      <div v-if="schema.description" class="schema-description">{{ schema.description }}</div>
    </template>
    <template v-else>
      <v-textarea
        :model-value="fallbackJson"
        :label="label"
        variant="outlined"
        rows="3"
        density="compact"
        readonly
      ></v-textarea>
      <div class="schema-description text-medium-emphasis">
        Unsupported schema type – edit as JSON instead.
      </div>
    </template>
  </div>
</template>

<style scoped>

.schema-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}

.schema-object-header {
  margin-bottom: 6px;
}

.schema-label {
  font-weight: 600;
}

.schema-required {
  color: rgb(var(--v-theme-error));
  margin-left: 4px;
}

.schema-description {
  font-size: 0.85rem;
  color: rgba(var(--v-theme-on-surface), 0.7);
}

.schema-object-body {
  border-left: 1px dashed rgba(var(--v-theme-primary), 0.4);
  padding-left: 10px;
}

.schema-level-0 > .schema-object-body {
  border-left: none;
  padding-left: 0;
}
</style>
