<template>
    <v-text-field
        :model-value="modelValue"
        @update:model-value="$emit('update:modelValue', $event)"
        @click:clear="$emit('update:modelValue', '')"
        density="compact"
        variant="outlined"
        hide-details
        clearable
        :label="label"
        prepend-inner-icon="mdi-magnify"
        class="pm-search"
    />
</template>

<script setup lang="ts">
defineProps<{
    modelValue?: string;
    label: string;
}>();

defineEmits<{
    (e: 'update:modelValue', value: string): void;
}>();
</script>