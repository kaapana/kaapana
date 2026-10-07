<script setup lang="ts">
import { ref } from 'vue'
import { pruneArtifacts } from '@/services/api'
import type { ArtifactPruneResponse } from '@/types/domain'

const pruning = ref(false)
const pruneError = ref<string | null>(null)
const pruneResult = ref<ArtifactPruneResponse | null>(null)

async function handlePruneArtifacts() {
  pruning.value = true
  pruneError.value = null
  try {
    const result = await pruneArtifacts()
    pruneResult.value = result
  } catch (error) {
    pruneError.value = error instanceof Error ? error.message : 'Failed to prune artifacts'
  } finally {
    pruning.value = false
  }
}
</script>

<template>
  <v-card class="maintenance-card elevation-8">
    <v-card-title class="d-flex align-center">
      <v-icon class="mr-3" color="primary">mdi-broom</v-icon>
      Artifact Pruning
    </v-card-title>
    <v-card-subtitle>
      Remove orphaned artifacts that no longer have matching data entities or metadata keys.
    </v-card-subtitle>
    <v-card-text>
      <v-alert v-if="pruneError" type="error" variant="tonal" border="start" class="mb-4">
        {{ pruneError }}
      </v-alert>
      <div v-if="pruneResult" class="mb-4">
        <div class="text-subtitle-2 mb-2">Last run summary</div>
        <v-list density="compact" class="result-list">
          <v-list-item>
            <v-list-item-title>Scanned files</v-list-item-title>
            <v-list-item-subtitle>{{ pruneResult.scanned_files }}</v-list-item-subtitle>
          </v-list-item>
          <v-list-item>
            <v-list-item-title>Deleted files</v-list-item-title>
            <v-list-item-subtitle>{{ pruneResult.deleted_files }}</v-list-item-subtitle>
          </v-list-item>
          <v-list-item>
            <v-list-item-title>Skipped files</v-list-item-title>
            <v-list-item-subtitle>{{ pruneResult.skipped_files }}</v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </div>
      <v-btn color="primary" :loading="pruning" :disabled="pruning" @click="handlePruneArtifacts">
        Run prune task
      </v-btn>
    </v-card-text>
  </v-card>
</template>

<style scoped>
.maintenance-card {
  min-height: 220px;
}

.result-list {
  background: transparent;
}
</style>
