<template>
  <v-card title="Archive Project" prepend-icon="mdi-archive-arrow-down">
    <v-card-text>
      <p class="mb-3">
        Archiving <strong>{{ project.name }}</strong> makes it read-only.
        Only <code>project-dicom-transfer</code> and <code>download-selected-files</code>
        workflows will remain available; data uploads, DICOM ingest/deletion,
        dataset edits, and user/role/software changes are blocked. Existing data
        and views remain accessible. You can unarchive at any time.
      </p>
      <v-alert type="warning" density="compact" variant="tonal" class="mb-1">
        If any workflows are currently running, please wait for them to finish before archiving,
        archiving while jobs are in flight may cause undefined behavior.
      </v-alert>
    </v-card-text>
    <v-card-actions>
      <v-spacer />
      <v-btn @click="$emit('cancel')">Cancel</v-btn>
      <v-btn color="warning" variant="elevated" @click="$emit('confirm')">Archive</v-btn>
    </v-card-actions>
  </v-card>
</template>

<script lang="ts">
import { defineComponent, PropType } from 'vue'
import { ProjectItem } from '@/common/types'

export default defineComponent({
  props: {
    project: { type: Object as PropType<ProjectItem>, required: true },
  },
  emits: ['confirm', 'cancel'],
})
</script>
