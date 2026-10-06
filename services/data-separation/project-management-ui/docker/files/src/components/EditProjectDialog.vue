<template>
  <v-card title="Edit Project" :prepend-icon="kaapanaIcons.edit">
    <v-card-text>
      <v-container>
        <v-row><v-col>
          <v-text-field v-model="form.name" label="Project Name" :rules="nameRules" />
        </v-col></v-row>
        <v-row><v-col>
          <v-text-field v-model="form.external_id" label="External ID" />
        </v-col></v-row>
        <v-row><v-col>
          <v-textarea v-model="form.description" label="Description" auto-grow rows="3" />
        </v-col></v-row>
      </v-container>
    </v-card-text>
    <v-card-actions>
      <v-spacer />
      <v-btn :disabled="saving" @click="$emit('cancel')">Cancel</v-btn>
      <v-btn
        color="primary"
        variant="elevated"
        :loading="saving"
        :disabled="saving"
        @click="submit"
      >
        Save
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script lang="ts">
import { kaapanaIcons } from '@/utils/projectIcons'
import { defineComponent, PropType } from 'vue'
import { aiiApiPut } from '@/common/services'
import { ProjectItem } from '@/common/types'
import { projectNameRules } from '@/common/validation'

export default defineComponent({
  setup() {
    return { kaapanaIcons }
  },
  props: {
    project: { type: Object as PropType<ProjectItem>, required: true },
  },
  emits: ['success', 'cancel', 'error'],
  data() {
    return {
      form: {
        name: this.project.name,
        description: this.project.description || '',
        external_id: this.project.external_id ? String(this.project.external_id) : '',
      },
      nameRules: projectNameRules,
      saving: false,
    }
  },
  watch: {
    project(newProject: ProjectItem) {
      this.form = {
        name: newProject.name,
        description: newProject.description || '',
        external_id: newProject.external_id ? String(newProject.external_id) : '',
      }
    },
  },
  methods: {
    async submit() {
      const nameError = this.nameRules.map(r => r(this.form.name)).find(r => r !== true)
      if (nameError) {
        this.$emit('error', String(nameError))
        return
      }
      this.saving = true
      try {
        await aiiApiPut(`projects/${this.project.id}`, {}, {
          name: this.form.name,
          description: this.form.description,
          external_id: this.form.external_id || null,
        })
        this.$emit('success')
      } catch (error: unknown) {
        this.$emit('error', `Could not save "${this.form.name}".`, error)
      } finally {
        this.saving = false
      }
    },
  },
})
</script>
