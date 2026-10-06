<template>
  <v-card title="Edit Project">
    <v-card-text>
      <v-form ref="form" @submit.prevent="submit">
        <v-text-field
          v-model="name"
          label="Project name"
          :rules="nameRules"
          :hint="projectNameHint"
          persistent-hint
          class="mb-2"
        />
        <v-textarea
          v-model="description"
          label="Description"
          :rules="[required('a description')]"
          auto-grow
          rows="3"
        />
        <v-text-field v-model="externalId" label="External ID (optional)" />
      </v-form>
      <FailureAlert
        v-if="failure"
        title="Project not updated"
        :text="failureText"
        :error="failure"
      />
    </v-card-text>
    <v-card-actions>
      <v-spacer />
      <v-btn :disabled="saving" @click="emit('cancel')">Cancel</v-btn>
      <v-btn color="primary" :loading="saving" :disabled="saving" @click="submit">Save</v-btn>
    </v-card-actions>
  </v-card>
</template>

<script lang="ts" setup>
import { computed, ref } from 'vue'
import { aiiApiPut } from '@/common/services'
import { ProjectItem } from '@/common/types'
import { projectNameHint, projectNameRules, required } from '@/common/validation'
import FailureAlert from '@/components/FailureAlert.vue'

const props = defineProps<{ project: ProjectItem }>()

const emit = defineEmits<{
  (e: 'success'): void
  (e: 'cancel'): void
}>()

const form = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)
const name = ref(props.project.name)
const description = ref(props.project.description ?? '')
const externalId = ref(props.project.external_id ?? '')
const saving = ref(false)
const failure = ref<unknown>(null)
const failureText = computed(() => `Could not save "${props.project.name}".`)
// Names from before the current rules stay valid as long as they are kept.
const nameRules = computed(() => (name.value === props.project.name ? [] : projectNameRules))

async function submit() {
  if (!(await form.value!.validate()).valid) return
  saving.value = true
  failure.value = null
  try {
    await aiiApiPut(
      `projects/${props.project.id}`,
      {},
      { name: name.value, description: description.value, external_id: externalId.value || null },
    )
    emit('success')
  } catch (error) {
    failure.value = error
  } finally {
    saving.value = false
  }
}
</script>
