<template>
  <!-- One deploy parameter, rendered from its declaration in helm-chart-content.json
       (Story 2.2). No appearance props: Vuetify's default field style. -->
  <v-switch
    v-if="decl.type === 'boolean'"
    :id="fieldId"
    :model-value="modelValue"
    :label="decl.label"
    :hint="decl.description"
    persistent-hint
    color="primary"
    inset
    class="mb-2"
    @update:model-value="emit('update:modelValue', !!$event)"
  />
  <v-select
    v-else-if="decl.type === 'choice'"
    :id="fieldId"
    :model-value="modelValue"
    :label="label"
    :items="items"
    item-title="title"
    item-value="value"
    :hint="decl.description"
    persistent-hint
    :rules="rules"
    class="mb-2"
    @update:model-value="emit('update:modelValue', $event)"
  />
  <v-text-field
    v-else-if="decl.type === 'integer'"
    :id="fieldId"
    :model-value="modelValue"
    :label="label"
    type="number"
    :min="decl.min"
    :max="decl.max"
    :hint="decl.description"
    persistent-hint
    :rules="rules"
    class="mb-2"
    @update:model-value="emit('update:modelValue', $event === '' ? '' : Number($event))"
  />
  <v-text-field
    v-else
    :id="fieldId"
    :model-value="modelValue"
    :label="label"
    :type="decl.secret ? 'password' : 'text'"
    :autocomplete="decl.secret ? 'new-password' : 'off'"
    :hint="decl.description"
    persistent-hint
    :rules="rules"
    class="mb-2"
    @update:model-value="emit('update:modelValue', $event)"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ParamDecl, ParamValue } from '@/mock/types'

const props = defineProps<{ decl: ParamDecl; modelValue: ParamValue; folders: string[] }>()
const emit = defineEmits<{ 'update:modelValue': [value: ParamValue] }>()

const fieldId = computed(() => `param-${props.decl.key}`)
const label = computed(() => (props.decl.required ? `${props.decl.label} *` : props.decl.label))

const items = computed(() => {
  const c = props.decl.choices
  if (c === 'project-folders') {
    return props.folders.map((f) => ({ title: f === '/' ? 'Whole bucket (/)' : `${f}/`, value: f }))
  }
  return c ?? []
})

// Every message names the parameter and says how to fix the value (Story 2.2, base-ui
// guideline "Validation").
const rules = computed(() => {
  const d = props.decl
  const out: ((v: unknown) => true | string)[] = []
  if (d.required) out.push((v) => (v !== '' && v !== null && v !== undefined) || `${d.label} is required.`)
  if (d.type === 'integer') {
    out.push((v) => v === '' || v === null || Number.isInteger(Number(v)) || `${d.label}: use a whole number.`)
    if (d.min !== undefined && d.max !== undefined) {
      const { min, max } = d
      out.push(
        (v) => v === '' || v === null || (Number(v) >= min && Number(v) <= max) || `${d.label}: use a value from ${min} to ${max}.`,
      )
    }
  }
  if (d.minLength) {
    const n = d.minLength
    out.push((v) => !v || String(v).length >= n || `${d.label}: use at least ${n} characters.`)
  }
  return out
})
</script>
