<template>
    <v-card prepend-icon="mdi-plus-box" title="Add New Project">
        <v-overlay v-model="fetching" class="align-center justify-center" contained>
            <v-progress-circular color="primary" indeterminate></v-progress-circular>
        </v-overlay>

        <v-card-text>
            <v-container>
                <v-row class="pb-6">
                    <v-alert 
                        density="compact"
                        text="Project name must follow Minio, OpenSearch, and Kubernetes naming convention, and be under 16 
                        characters. Use a short, lowercase, alphanumeric name (max 16 chars), with - as a separator. 
                        Avoid spaces and the word 'project' within the name."
                        type="info"
                        variant="tonal"
                    ></v-alert>
                </v-row>
                <v-row>
                    <v-text-field v-model="name" label="Project Name" :rules="project_name_rules"></v-text-field>
                </v-row>
                <v-row><v-text-field v-model="description" label="Description" required></v-text-field></v-row>
                <v-row><v-text-field v-model="external_id" label="External ID"></v-text-field></v-row>
            </v-container>
        </v-card-text>
        <v-card-actions>
            <v-container>
                <v-row>
                    <v-col cols="6">
                        <v-btn color="surface-variant" size="large" variant="elevated" block
                            @click="cancel">Cancel</v-btn>
                    </v-col>
                    <v-col cols="6">
                        <v-btn :disabled="!valid" color="success" size="large" variant="elevated" block
                            @click="submit">Submit</v-btn>
                    </v-col>
                </v-row>
            </v-container>
        </v-card-actions>
    </v-card>
</template>

<script lang="ts" setup>
import { ref, computed } from 'vue';
import { aiiApiPost } from '@/common/aiiApi.service';
// import {AxiosError} from axios;



const props = defineProps({
    oncancel: {
        type: Function,
    },
    onsuccess: {
        type: Function,
    }
});

const name = ref('');
const description = ref('');
const external_id = ref('');
const fetching = ref(false)

// Early validation rules for project naming from the UI
const project_name_rules = ref<Array<(value: string) => boolean | string>>([
  (value) => !!value || 'Required.',
  (value) => (value && value.length <= 16) || 'Max 16 characters',
  (value) => (value == value.toLowerCase()) || 'Only lowercase alphanumeric characters are supported',
  (value) => (!value.includes(" ")) || 'Space are not allowed',
]);

const valid = computed(() => {
    let validate_name = true;
    for (const rule of project_name_rules.value) {
        const result = rule(name.value);
        if (result !== true) {
            validate_name = false;
            break;
        }
    }
    return (validate_name && (description.value.trim() !== ''));
})

const submit = async () => {
    const data = {
        "external_id": external_id.value.trim(),
        "name": name.value.trim(),
        "description": description.value.trim()
    }
    fetching.value = true;

    try {
        await aiiApiPost(`projects`, data);
        fetching.value = false;
        props.onsuccess?.();
    } catch (error: unknown) {
        fetching.value = false;
        props.onsuccess?.(false);       
    }
}

const cancel = () => {
    props.oncancel?.();
}

</script>