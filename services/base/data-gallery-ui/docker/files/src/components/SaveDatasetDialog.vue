<template>
  <div>
    <v-dialog v-model="show" width="500">
      <v-card>
        <v-card-title> Save Dataset </v-card-title>
        <v-card-text>
          <v-text-field v-model="name" label="Name" clearable></v-text-field>
          <v-select
            v-model="access_level"
            label="Access Level"
            :items="['private', 'project']"
          ></v-select>
        </v-card-text>
        <v-divider></v-divider>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" :disabled="name === ''" @click.stop="save">Save</v-btn>
          <v-btn @click.stop="show = false">Cancel</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  save: [name: string, accessLevel: string]
  cancel: [value: boolean]
}>()

const name = ref('')
const access_level = ref('private')

function save() {
  emit('save', name.value, access_level.value)
  name.value = ''
  access_level.value = 'private'
}

const show = computed({
  get() {
    return props.modelValue
  },
  set(value: boolean) {
    name.value = ''
    access_level.value = 'private'
    emit('cancel', value)
  },
})
</script>

<style scoped></style>
