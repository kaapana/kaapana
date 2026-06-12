<template>
    <v-dialog v-model="dialog" max-width="1200px">
        <v-card>
            <v-card-title class="bg-primary text-white">
                <span class="text-h5">Application Parameters</span>
            </v-card-title>
            <v-card-text>
                <v-alert v-if="!extensionParams || Object.keys(extensionParams).length === 0" type="info" class="mb-0">
                    No extension parameters available
                </v-alert>
                <v-container v-else class="pa-3">
                    <v-row v-for="(value, key) in extensionParams" :key="key" class="mb-2">
                        <v-col cols="12" md="3" class="font-weight-medium text-sm">
                            {{ formatParamName(key) }}
                        </v-col>
                        <v-col cols="12" md="9">
                            <v-switch
                                v-if="typeof value === 'boolean'"
                                :model-value="value"
                                readonly
                                color="primary"
                                inset
                            ></v-switch>
                            <v-card v-else variant="tonal" class="pa-2">
                                <pre class="text-body-2 text-pre-wrap mb-0">{{ formatValue(value) }}</pre>
                            </v-card>
                        </v-col>
                    </v-row>
                </v-container>
            </v-card-text>
            <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn color="primary" variant="text" @click="closeDialog">
                    Close
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script lang="ts" setup>
import { computed } from 'vue';

const props = defineProps<{
    modelValue: boolean;
    application: {
        release_name?: string;
        values?: Record<string, any>;
        pods?: Array<{
            name: string;
            status: string;
            restartCount?: number;
        }>;
    } | null;
}>();

const emit = defineEmits<{
    (e: 'update:modelValue', value: boolean): void;
    (e: 'close'): void;
}>();

const dialog = computed({
    get: () => props.modelValue,
    set: (value) => {
        emit('update:modelValue', value);
    }
});

// ── Computed properties for dialog ─────────────────────────────────────────

const extensionParams = computed(() => {
    if (!props.application?.values) return {};
    // Extract extension_params if it exists
    const values = props.application.values;
    const extensionParamsRaw = values.extension_params || {};
    
    // Flatten the extension_params to extract actual values
    const flattened: Record<string, any> = {};
    for (const [key, value] of Object.entries(extensionParamsRaw)) {
        if (value && typeof value === 'object') {
            // Use 'value' if it exists and is not empty; otherwise use 'default'
            const actualValue = (value as any).value;
            flattened[key] = (actualValue !== undefined && actualValue !== null && actualValue !== '') 
                ? actualValue 
                : (value as any).default;
        } else {
            flattened[key] = value;
        }
    }
    return flattened;
});

// ── Methods ────────────────────────────────────────────────────────────────

const closeDialog = () => {
    emit('update:modelValue', false);
    emit('close');
};

const formatParamName = (key: string | number): string => {
    // Convert dot notation to readable format
    // e.g., "extension_params.display_name.default" -> "Display Name Default"
    const keyStr = String(key);
    const parts = keyStr.split('.');
    const lastPart = parts[parts.length - 1];
    return lastPart
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (char) => char.toUpperCase());
};

const formatValue = (value: any): string | boolean => {
    if (value === null || value === undefined) {
        return 'null';
    }
    if (typeof value === 'boolean') {
        return value;
    }
    if (typeof value === 'string') {
        return value;
    }
    if (typeof value === 'object') {
        return JSON.stringify(value, null, 2);
    }
    return String(value);
};
</script>
