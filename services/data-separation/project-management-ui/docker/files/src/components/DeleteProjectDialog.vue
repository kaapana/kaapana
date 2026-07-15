<template>
  <v-card title="Delete Project" prepend-icon="mdi-trash-can">
    <v-card-text>
      <p class="mb-2">
        Are you sure you want to delete <strong>{{ project.name }}</strong>?
      </p>
      <p class="text-caption text-medium-emphasis">
        All data in this project that is not used in any other project will be permanently deleted from the platform.
        To keep the data while making the project read-only, archive it instead.
      </p>
    </v-card-text>
    <v-card-actions>
      <v-spacer />
      <v-btn @click="$emit('cancel')">Cancel</v-btn>
      <v-btn color="error" variant="elevated" @click="$emit('confirm')">
        Delete
      </v-btn>
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
