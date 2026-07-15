<template>
    <v-card title="Create New Project">
      <template #prepend><v-icon color="primary">mdi-plus-box</v-icon></template>

        <v-card-text>
            <v-container>
                <v-row class="pb-6">
                    <v-alert 
                        density="compact"
                        text="Project name must follow Minio, OpenSearch, and Kubernetes naming convention, and be under 16 
                        characters. Use a short, lowercase, alphanumeric name (max 13 chars), with - as a separator. 
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
                        <v-btn size="large" variant="tonal" block
                            @click="cancel">Cancel</v-btn>
                    </v-col>
                    <v-col cols="6">
                        <v-btn :disabled="!valid" color="primary" size="large" variant="flat" block
                            @click="submit">Create</v-btn>
                    </v-col>
                </v-row>
            </v-container>
        </v-card-actions>
    </v-card>
</template>

<script lang="ts" setup>
import { ref, computed } from 'vue';
import { aiiApiPost } from '@/common/services';
import { projectNameRules } from '@/common/validation';



const props = defineProps({
    oncancel: {
        type: Function,
    },
    onsuccess: {
        type: Function,
    },
    oncomplete: {
        type: Function,
    }
});

const name = ref('');
const description = ref('');
const external_id = ref('');

const project_name_rules = ref(projectNameRules);

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

const submit = () => {
    const data = {
        "external_id": external_id.value.trim(),
        "name": name.value.trim(),
        "description": description.value.trim()
    }

    props.onsuccess?.();

    aiiApiPost(`projects`, data)
        .then(() => props.oncomplete?.())
        .catch(() => props.oncomplete?.(false));
}

const cancel = () => {
    props.oncancel?.();
}

</script>