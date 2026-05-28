<template>
  <v-card title="Edit Project" prepend-icon="mdi-pencil">
    <v-card-text>
      <v-container>
        <v-row><v-col>
          <v-text-field v-model="form.name" label="Project Name" :rules="nameRules" />
        </v-col></v-row>
        <v-row><v-col>
          <v-text-field v-model="form.description" label="Description" />
        </v-col></v-row>
        <v-row><v-col>
          <v-text-field v-model="form.external_id" label="External ID" />
        </v-col></v-row>
      </v-container>
    </v-card-text>
    <v-card-actions>
      <v-spacer />
      <v-btn @click="$emit('cancel')">Cancel</v-btn>
      <v-btn color="primary" variant="elevated" @click="submit">Save</v-btn>
    </v-card-actions>
  </v-card>
</template>

<script lang="ts">
import { defineComponent, PropType } from 'vue'
import { aiiApiPut } from '@/common/aiiApi.service'
import { ProjectItem } from '@/common/types'
import { projectNameRules } from '@/common/validation'

export default defineComponent({
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
      try {
        await aiiApiPut(`projects/${this.project.id}`, {}, {
          name: this.form.name,
          description: this.form.description,
          external_id: this.form.external_id || null,
        })
        this.$emit('success')
      } catch (error: unknown) {
        this.$emit('error', 'Failed to update project.')
      }
    },
  },
})
</script>
