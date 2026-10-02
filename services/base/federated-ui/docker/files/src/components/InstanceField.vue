<script setup lang="ts">
import { kaapanaIcons } from '@/utils/icons'

const props = defineProps<{
  label: string
  editable?: boolean
  editing?: boolean
  locked?: boolean
  saving?: boolean
  canSave?: boolean
}>()

const emit = defineEmits<{ edit: []; save: []; cancel: [] }>()

function submit() {
  if (props.canSave && !props.saving) emit('save')
}
</script>

<template>
  <div class="instance-field" :data-field="props.label">
    <dt class="text-body-2 text-medium-emphasis">{{ props.label }}</dt>
    <dd class="text-body-2">
      <v-form v-if="props.editing" @submit.prevent="submit">
        <slot name="edit" />
      </v-form>
      <slot v-else />
    </dd>
    <div class="instance-field-actions">
      <template v-if="props.editing">
        <v-btn
          :icon="kaapanaIcons.save"
          color="primary"
          variant="text"
          size="small"
          :aria-label="`Save ${props.label}`"
          :loading="props.saving"
          :disabled="props.saving || !props.canSave"
          @click="submit"
        />
        <v-btn
          :icon="kaapanaIcons.close"
          variant="text"
          size="small"
          :aria-label="`Cancel editing ${props.label}`"
          :disabled="props.saving"
          @click="emit('cancel')"
        />
      </template>
      <v-btn
        v-else-if="props.editable"
        :icon="kaapanaIcons.edit"
        variant="text"
        size="small"
        :aria-label="`Edit ${props.label}`"
        :disabled="props.locked"
        @click="emit('edit')"
      />
    </div>
  </div>
</template>

<style scoped>
.instance-field {
  display: grid;
  grid-template-columns: minmax(9rem, 13rem) minmax(0, 1fr) 5rem;
  column-gap: 16px;
  align-items: center;
  min-height: 44px;
}

.instance-field dd {
  min-width: 0;
  overflow-wrap: anywhere;
}

.instance-field-actions {
  display: flex;
  justify-content: flex-end;
}
</style>
