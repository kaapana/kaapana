<script setup lang="ts">
import { inject } from 'vue'
import { icons } from '@/utils/icons'
import { CHIP_BUILDER_KEY, type ChipBuilderContext } from './types'

const ctx = inject<ChipBuilderContext>(CHIP_BUILDER_KEY)!
</script>

<template>
  <div class="composer border rounded pa-2" data-testid="condition-composer">
    <v-autocomplete
      :ref="ctx.setFieldInputRef"
      v-model="ctx.builderField.value"
      :items="ctx.fieldItems.value"
      :loading="ctx.metadataFieldLoading.value"
      :error-messages="ctx.metadataFieldError.value ?? undefined"
      label="Field"
      placeholder="e.g. metadata.sample.batch"
      density="compact"
      hide-no-data
      clearable
      :hide-details="!ctx.metadataFieldError.value"
      class="composer-field"
      @keydown.enter.prevent="ctx.advanceFromField"
      @keydown.esc.prevent.stop="ctx.handleComposerEscape"
    />
    <v-select
      v-if="ctx.canShowOperator.value"
      :ref="ctx.setOperatorSelectRef"
      v-model="ctx.builderOp.value"
      :items="ctx.effectiveOperatorItems.value"
      label="Operator"
      density="compact"
      hide-details
      class="composer-operator"
      @keydown.enter.prevent="ctx.advanceFromOperator"
      @keydown.esc.prevent.stop="ctx.handleComposerEscape"
    />
    <template v-if="ctx.canShowValue.value">
      <v-select
        v-if="ctx.isArrayField.value"
        :ref="ctx.setValueInputRef"
        v-model="ctx.builderArraySelections.value"
        :items="ctx.builderArrayValueOptions.value"
        :loading="ctx.builderValueLoading.value"
        :label="ctx.builderValueLabel.value"
        item-title="label"
        item-value="token"
        multiple
        chips
        density="compact"
        hide-details
        clearable
        class="composer-value"
        @keydown.enter.prevent="ctx.advanceFromValue"
        @keydown.esc.prevent.stop="ctx.handleComposerEscape"
      />
      <v-combobox
        v-else
        :ref="ctx.setValueInputRef"
        v-model="ctx.builderValue.value"
        :items="ctx.builderValueSuggestions.value"
        :loading="ctx.builderValueLoading.value"
        :label="ctx.builderValueLabel.value"
        placeholder="A value, JSON, or a comma-separated list"
        density="compact"
        hide-no-data
        hide-details
        clearable
        class="composer-value"
        @keydown.enter.prevent="ctx.advanceFromValue"
        @keydown.esc.prevent.stop="ctx.handleComposerEscape"
      />
    </template>
    <v-btn
      color="primary"
      variant="tonal"
      :prepend-icon="icons.confirm"
      :disabled="ctx.isLoading.value || !ctx.canCommitChip.value"
      @click.stop="ctx.commitChip"
    >
      {{ ctx.isEditingExisting.value ? 'Update condition' : 'Add condition' }}
    </v-btn>
    <v-btn variant="text" @click.stop="ctx.resetBuilder">Cancel</v-btn>
  </div>
</template>

<style scoped>
.composer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.composer-field,
.composer-value {
  flex: 1 1 240px;
}

.composer-operator {
  flex: 0 1 180px;
}
</style>
