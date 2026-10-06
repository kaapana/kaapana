<script setup lang="ts">
import { useFocusReturn } from '@/composables/useFocusReturn'
const model = defineModel<boolean>({ required: true })
const restoreFocus = useFocusReturn(model)

const shortcuts = [
  { combo: 'F', description: 'Open the filter and start a new condition' },
  { combo: 'C', description: 'Copy the filter as JSON' },
  { combo: 'P', description: 'Paste a filter from the clipboard and apply it' },
  { combo: 'X', description: 'Clear the filter' },
  { combo: '+', description: 'Show more entities per row' },
  { combo: '-', description: 'Show fewer entities per row' },
  { combo: '?', description: 'Show the keyboard shortcuts' },
]
</script>

<template>
  <v-dialog v-model="model" max-width="400" @after-leave="restoreFocus">
    <v-card :elevation="5">
      <v-card-title>Keyboard shortcuts</v-card-title>
      <v-card-text>
        <p class="text-body-2 text-medium-emphasis mb-3">
          Shortcuts work while no text field has the focus.
        </p>
        <v-table density="compact">
          <tbody>
            <tr v-for="shortcut in shortcuts" :key="shortcut.combo">
              <td class="shortcut-key">
                <kbd>{{ shortcut.combo }}</kbd>
              </td>
              <td>{{ shortcut.description }}</td>
            </tr>
          </tbody>
        </v-table>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn color="primary" @click="model = false">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.shortcut-key {
  width: 48px;
}
</style>
