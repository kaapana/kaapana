<template>
  <!-- Large (900 px): it holds a table. The technical detail stays behind this
       disclosure; the alert on the page carries the sentence a scientist can act on. -->
  <v-dialog :model-value="modelValue" max-width="900" @update:model-value="emit('update:modelValue', $event)">
    <v-card v-if="app" :elevation="5">
      <v-card-title class="text-wrap">Why "{{ app.name }}" is not running</v-card-title>
      <v-card-text>
        <p class="mb-4">{{ app.failure?.reason }}</p>
        <div class="text-subtitle-2 mb-1">Helm</div>
        <pre class="detail pa-3 mb-4">{{ app.failure?.helm }}</pre>
        <template v-if="app.events.length">
          <div class="text-subtitle-2 mb-1">Kubernetes events</div>
          <v-table density="compact">
            <thead>
              <tr>
                <th>Type</th>
                <th>Reason</th>
                <th>Object</th>
                <th>Message</th>
                <th>Age</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(e, i) in app.events" :key="i">
                <td>
                  <v-icon
                    size="small"
                    :icon="e.type === 'Warning' ? kaapanaIcons.warning : kaapanaIcons.info"
                    :color="e.type === 'Warning' ? 'warning' : undefined"
                    class="mr-1"
                  />{{ e.type }}
                </td>
                <td>{{ e.reason }}</td>
                <td class="text-caption">{{ e.object }}</td>
                <td>{{ e.message }}</td>
                <td>{{ age(e.at) }}</td>
              </tr>
            </tbody>
          </v-table>
        </template>
      </v-card-text>
      <v-card-actions>
        <v-btn variant="text" :prepend-icon="copied ? kaapanaIcons.confirm : kaapanaIcons.copy" @click="copy">
          {{ copied ? 'Copied' : 'Copy details' }}
        </v-btn>
        <v-spacer />
        <v-btn autofocus @click="emit('update:modelValue', false)">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { kaapanaIcons } from '@kaapana/base-ui'
import type { DeployedApp } from '@/mock/types'
import { age } from '@/utils/format'

const props = defineProps<{ modelValue: boolean; app: DeployedApp | null }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()
const copied = ref(false)

async function copy() {
  const a = props.app
  if (!a) return
  const text = [
    `${a.name}: ${a.failure?.reason}`,
    `Helm: ${a.failure?.helm}`,
    ...a.events.map((e) => `${e.type} ${e.reason} ${e.object}: ${e.message}`),
  ].join('\n')
  try {
    await navigator.clipboard.writeText(text)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch {
    // No clipboard outside secure contexts; the text stays selectable.
  }
}
</script>

<style scoped>
.detail {
  white-space: pre-wrap;
  font-family: monospace;
  font-size: 0.8125rem;
  background: rgb(var(--v-theme-surface-light));
  border-radius: 8px;
}
</style>
