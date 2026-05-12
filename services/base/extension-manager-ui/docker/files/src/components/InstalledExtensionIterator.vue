<script setup lang="ts">
import type { InstalledExtension } from '@/types/schemas'

const props = defineProps<{
  installedExtensions: InstalledExtension[]
  loadingInstalledExtensions: boolean
  installedExtensionsError?: string | null
}>()

const emit = defineEmits<{
  (event: 'selectInstalledExtension', installedExtension: InstalledExtension): void
}>()

function emitSelectInstalledExtension(installedExtension: InstalledExtension) {
  emit('selectInstalledExtension', installedExtension)
}
</script>

<template>
  <v-alert v-if="props.installedExtensionsError" type="error" class="mb-4">
    {{ props.installedExtensionsError }}
  </v-alert>

  <v-row v-else-if="props.loadingInstalledExtensions" class="d-flex justify-center align-center" style="min-height: 240px;">
    <v-progress-circular indeterminate color="primary" size="64" />
  </v-row>

  <v-alert v-else-if="props.installedExtensions.length === 0" type="info" class="mb-4">
    No extensions currently have platform state.
  </v-alert>

  <v-row v-else>
    <v-col
      v-for="installedExtension in props.installedExtensions"
      :key="installedExtension.id"
      cols="12"
      md="6"
      lg="4"
    >
      <v-card
        class="h-100"
        role="button"
        tabindex="0"
        @click="emitSelectInstalledExtension(installedExtension)"
      >
        <v-card-title>
          {{ installedExtension.manifest.name }}
        </v-card-title>

        <v-card-subtitle>
          {{ installedExtension.manifest.version }} · {{ installedExtension.tag }}
        </v-card-subtitle>

        <v-card-text class="d-flex flex-column ga-2">
          <div>
            <v-chip size="small" color="primary" variant="tonal">
              {{ installedExtension.status }}
            </v-chip>
          </div>

          <div class="text-caption text-medium-emphasis">
            Repository: {{ installedExtension.repository_id }}
          </div>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>
