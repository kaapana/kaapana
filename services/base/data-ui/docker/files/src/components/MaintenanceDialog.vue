<script setup lang="ts">
import { useFocusReturn } from '@/composables/useFocusReturn'
import { ref } from 'vue'
import { ConfirmDialog } from '@kaapana/base-ui'
import { pruneArtifacts } from '@/services/api'
import type { ArtifactPruneResponse } from '@/types/domain'
import { notifyFailure, notifySuccess } from '@/utils/notify'

const model = defineModel<boolean>({ required: true })
const restoreFocus = useFocusReturn(model)

const confirmOpen = ref(false)
const pruning = ref(false)
const pruneResult = ref<ArtifactPruneResponse | null>(null)

async function prune() {
  pruning.value = true
  try {
    pruneResult.value = await pruneArtifacts()
    const deleted = pruneResult.value.deleted_files
    notifySuccess(
      'Artifacts pruned',
      `${deleted} orphaned artifact file${deleted === 1 ? ' was' : 's were'} deleted.`,
    )
  } catch (error) {
    notifyFailure('Artifacts not pruned', 'The orphaned artifact files could not be pruned.', error)
  } finally {
    pruning.value = false
  }
}
</script>

<template>
  <v-dialog v-model="model" max-width="600" @after-leave="restoreFocus">
    <v-card :elevation="5">
      <v-card-title>Maintenance</v-card-title>
      <v-card-text>
        <h2 class="text-h6 mb-1">Prune orphaned artifacts</h2>
        <p class="text-body-2 text-medium-emphasis mb-4">
          Deletes artifact files on disk that no longer belong to any entity or metadata entry. The
          pruning covers the artifact storage of all projects.
        </p>
        <v-table v-if="pruneResult" density="compact" class="mb-2" data-testid="prune-result">
          <tbody>
            <tr>
              <td>Files scanned</td>
              <td class="text-right">{{ pruneResult.scanned_files }}</td>
            </tr>
            <tr>
              <td>Files deleted</td>
              <td class="text-right">{{ pruneResult.deleted_files }}</td>
            </tr>
            <tr>
              <td>Files kept</td>
              <td class="text-right">{{ pruneResult.skipped_files }}</td>
            </tr>
          </tbody>
        </v-table>
      </v-card-text>
      <v-card-actions>
        <v-btn color="error" variant="text" :loading="pruning" @click="confirmOpen = true">
          Prune artifacts
        </v-btn>
        <v-spacer />
        <v-btn @click="model = false">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
  <ConfirmDialog
    v-model="confirmOpen"
    title="Prune orphaned artifacts?"
    text="Artifact files that no longer belong to an entity are deleted permanently, in all projects. Files of existing entities are kept."
    confirm-text="Prune artifacts"
    color="error"
    @confirm="prune"
  />
</template>
