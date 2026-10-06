<template>
    <v-card title="Create New Project">
        <v-card-text>
            <v-form ref="form" @submit.prevent="submit">
                <v-text-field
                    v-model="name"
                    label="Project name"
                    :rules="projectNameRules"
                    :hint="projectNameHint"
                    persistent-hint
                    class="mb-2"
                />
                <v-textarea
                    v-model="description"
                    label="Description"
                    :rules="[required('a description')]"
                    auto-grow
                    rows="3"
                />
                <v-text-field v-model="externalId" label="External ID (optional)" />
            </v-form>
            <FailureAlert
                v-if="failure"
                title="Project not created"
                text="The project could not be created."
                :error="failure"
            />
        </v-card-text>
        <v-card-actions>
            <v-spacer />
            <v-btn :disabled="saving" @click="emit('cancel')">Cancel</v-btn>
            <v-btn color="primary" :loading="saving" :disabled="saving" @click="submit">
                Create project
            </v-btn>
        </v-card-actions>
    </v-card>
</template>

<script lang="ts" setup>
import { ref } from 'vue'
import { notify } from '@kyvg/vue3-notification'
import { refreshShell } from '@kaapana/base-ui'
import { aiiApiPost } from '@/common/services'
import { projectNameHint, projectNameRules, required } from '@/common/validation'
import FailureAlert from '@/components/FailureAlert.vue'

const emit = defineEmits<{
    (e: 'created'): void
    (e: 'cancel'): void
}>()

const form = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)
const name = ref('')
const description = ref('')
const externalId = ref('')
const saving = ref(false)
const failure = ref<unknown>(null)

async function submit() {
    if (!(await form.value!.validate()).valid) return
    saving.value = true
    failure.value = null
    try {
        await aiiApiPost('projects', {
            external_id: externalId.value.trim(),
            name: name.value.trim(),
            description: description.value.trim(),
        })
        refreshShell()
        notify({ type: 'success', text: `Project "${name.value.trim()}" created.` })
        emit('created')
    } catch (error) {
        failure.value = error
    } finally {
        saving.value = false
    }
}

</script>