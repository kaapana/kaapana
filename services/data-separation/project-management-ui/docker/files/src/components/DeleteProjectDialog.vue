<template>
  <v-card title="Delete Project" prepend-icon="mdi-trash-can">
    <v-card-text>
      <p class="mb-4">
        Are you sure you want to delete <strong>{{ project.name }}</strong>?
        Choose what happens to the project's data:
      </p>
      <v-radio-group v-model="retainData" class="mt-2">
        <v-radio :value="false" color="error">
          <template #label>
            <div>
              <div class="font-weight-medium">Delete data</div>
              <div class="text-caption text-medium-emphasis">
                All data in this project that is not used in any other project will be permanently deleted from the platform.
              </div>
            </div>
          </template>
        </v-radio>
        <v-radio :value="true" color="warning" class="mt-2">
          <template #label>
            <div>
              <div class="font-weight-medium">Retain data</div>
              <div class="text-caption text-medium-emphasis">
                Project access and configuration are removed, but the underlying data (S3 bucket, OpenSearch index) is preserved.
              </div>
            </div>
          </template>
        </v-radio>
      </v-radio-group>
    </v-card-text>
    <v-card-actions>
      <v-spacer />
      <v-btn @click="$emit('cancel')">Cancel</v-btn>
      <v-btn :color="retainData ? 'warning' : 'error'" variant="elevated" @click="$emit('confirm', retainData)">
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
  data() {
    return {
      retainData: false,
    }
  },
})
</script>
