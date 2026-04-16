<template>
    <v-text-field :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)"
        @click:clear="$emit('update:modelValue', '')" density="compact" variant="outlined" hide-details clearable
        :placeholder="placeholder" prepend-inner-icon="mdi-magnify" class="search-bar" />
</template>

<script setup lang="ts">
defineProps<{
    modelValue?: string;
    placeholder?: string;
}>();

const emit = defineEmits<{
    (e: 'update:modelValue', value: string): void;
}>();
</script>