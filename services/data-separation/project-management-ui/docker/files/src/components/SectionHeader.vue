<template>
    <v-row justify="space-between" class="align-center">

        <!-- LEFT SIDE -->
        <v-col cols="12" md="6">
            <div class="d-flex align-center gap-2 cursor-pointer w-fit" style="user-select: none;"
                @click="emit('toggle', !expanded)">

                <!-- icon -->
                <v-btn :icon="expanded ? 'mdi-chevron-down' : 'mdi-chevron-right'" variant="text"
                    @click.stop="emit('toggle', !expanded)" />

                <!-- TITLE -->
                <h5 class="text-h5 py-4 ml-2">
                    <slot name="title" />
                </h5>

                <!-- OPTIONAL CHIP / META -->
                <slot name="meta" />

            </div>
        </v-col>

        <!-- RIGHT SIDE -->
        <v-col cols="12" md="6" class="d-flex justify-end align-center ga-4" @click.stop>
            <slot name="actions" />
        </v-col>

    </v-row>
</template>

<script setup lang="ts">
defineProps<{
    expanded: boolean
}>()

const emit = defineEmits<{
    (e: 'toggle', value: boolean): void
}>()
</script>