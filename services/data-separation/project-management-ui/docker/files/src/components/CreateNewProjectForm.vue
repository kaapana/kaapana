<template>
    <v-card prepend-icon="mdi-plus-box" title="Add New Project">
        <v-card-text>
            <v-container>
                <v-row><v-text-field v-model="name" label="Project Name" required></v-text-field></v-row>
                <v-row><v-text-field v-model="description" label="Description" required></v-text-field></v-row>
                <v-row><v-text-field v-model="external_id" label="External ID"></v-text-field></v-row>
            </v-container>
        </v-card-text>
        <v-card-action>
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
        </v-card-action>
    </v-card>
</template>

<script lang="ts" setup>
import { ref, computed } from 'vue';
import axios, { AxiosResponse, AxiosRequestConfig, RawAxiosRequestHeaders } from 'axios';

const ACCESS_INFORMATION_BACKEND = import.meta.env.VITE_APP_ACCESS_INFORMATION_BACKEND || '/aii/';
const client = axios.create({
  baseURL: ACCESS_INFORMATION_BACKEND,
});


const props = defineProps({
    onsubmit: {
        type: Function,
    }
});

const name = ref('');
const description = ref('');
const external_id = ref('');

const valid = computed(() => {
    return ((name.value !== '') && (description.value !== ''));
})

const submit = async () => {
    // console.log(name.value, description.value, external_id.value);
    // console.log(valid.value);

    const config: AxiosRequestConfig = {
        headers: {
        'Accept': 'application/json',
        } as RawAxiosRequestHeaders,
    };
    
    const data = {
        "external_id": external_id.value,
        "name": name.value,
        "description": description.value
    }

    try {
      const response: AxiosResponse = await client.post(`projects`, data, config);
      console.log(response.status)
      props.onsubmit?.();
    } catch (error: unknown) {
      console.log(error)
    }
}

const cancel = () => {
    props.onsubmit?.();
}

</script>