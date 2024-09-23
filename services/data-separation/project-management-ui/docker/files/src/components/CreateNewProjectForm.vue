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
import { aiiApiPost } from '@/common/aiiApi.service';



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

const valid = computed(() => {
    return ((name.value !== '') && (description.value !== ''));
})

const submit = async () => {
    const data = {
        "external_id": external_id.value,
        "name": name.value,
        "description": description.value
    }

    try {
      await aiiApiPost(`projects`, data);
      props.onsuccess?.();      
    } catch (error: unknown) {
      console.log(error);
      props.oncancel?.();
    }
}

const cancel = () => {
    props.oncancel?.();
}

</script>