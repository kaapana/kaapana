<template>
  <!-- The shell, not the view, asks before unsaved work is left: the view only reports
       that it is dirty (base-ui guideline "Unsaved changes"). -->
  <v-dialog
    :model-value="!!mock.pendingLeave"
    max-width="400"
    @update:model-value="(open: boolean) => !open && keep()"
  >
    <v-card :elevation="5">
      <v-card-title>Leave without saving?</v-card-title>
      <v-card-text>{{ text }}</v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn autofocus @click="keep">Keep editing</v-btn>
        <v-btn color="error" @click="discard">Discard changes</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMockStore } from '@/stores/mock'

const mock = useMockStore()
const router = useRouter()

const text = computed(() => {
  const p = mock.pendingLeave
  if (p?.kind === 'project')
    return `Switching to ${mock.projectName(p.id)} reloads this view. The deploy form you started will be lost.`
  if (p?.kind === 'persona')
    return 'Switching the person reloads this view. The deploy form you started will be lost.'
  return 'The deploy form you started will be lost.'
})

function keep() {
  mock.pendingLeave = null
}

function discard() {
  const p = mock.pendingLeave
  mock.pendingLeave = null
  mock.dirty = false
  if (!p) return
  if (p.kind === 'route') router.push(p.to)
  else if (p.kind === 'project') mock.projectId = p.id
  else mock.applyPersona(p.id)
}
</script>
