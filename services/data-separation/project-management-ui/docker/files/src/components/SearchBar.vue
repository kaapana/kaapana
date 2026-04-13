<template>
    <v-text-field
        v-model="model"
        density="compact"
        variant="outlined"
        hide-details
        clearable
        :placeholder="placeholder"
        prepend-inner-icon="mdi-magnify"
        class="search-bar"
    />
</template>

<script setup lang="ts">
const model = defineModel<string>({ default: '' });

defineProps<{
    placeholder?: string;
}>();
</script>