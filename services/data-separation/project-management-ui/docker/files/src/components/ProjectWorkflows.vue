<template>
    <v-col>
        <!-- ── Section header ─────────────────────────────────────── -->
        <SectionHeader :expanded="props.expanded" @toggle="emit('toggle', $event)">
            <template #title>Project Workflows</template>

            <template #meta>
                <v-chip v-if="filteredWorkflows.length > 0" size="small" color="primary" variant="tonal">
                    {{ filteredWorkflows.length }}
                </v-chip>
            </template>

            <template #actions>
                <template v-if="can(project?.id, 'manage_workflow_whitelist')">
                    <v-chip v-if="pendingCount > 0" color="warning" variant="tonal" size="small">
                        {{ pendingCount }} unsaved change{{ pendingCount !== 1 ? 's' : '' }}
                    </v-chip>
                    <v-btn v-if="pendingCount > 0" size="small" variant="text" @click="discardChanges">
                        Discard
                    </v-btn>
                    <v-btn
                        :disabled="pendingCount === 0 || isSaving"
                        :loading="isSaving"
                        color="primary"
                        :prepend-icon="kaapanaIcons.save"
                        @click="saveChanges"
                    >
                        Save Changes
                    </v-btn>
                </template>
            </template>
        </SectionHeader>

        <!-- ── Expanded content ────────────────────────────────────── -->
        <v-expand-transition>
            <div v-if="props.expanded">
                <!-- search -->
                <SearchBar v-model="search" label="Search workflows" />

                <FailureAlert
                    v-if="loadError"
                    title="Workflows not loaded"
                    text="Could not load the workflows or this project's workflow whitelist."
                    :error="loadError"
                    :retry="loadWorkflows"
                />

                <!-- Workflow table -->
                <v-data-table
                    v-else
                    :loading="isLoading"
                    loading-text="Loading workflows…"
                    :items-per-page="-1"
                    hide-default-footer
                    :headers="tableHeaders"
                    :items="filteredWorkflows"
                    :sort-by="[{ key: 'dag_name', order: 'asc' }]"
                    multi-sort
                    class="mt-4"
                >
                    <template #item.icon>
                        <v-icon :icon="projectIcons.workflow" />
                    </template>

                    <template #item.dag_name="{ item }">
                        <span class="font-weight-medium">{{ item.dag_name }}</span>
                    </template>

                    <template #item.inAii="{ item }">
                        <v-checkbox-btn
                            :model-value="effectiveInAii(item)"
                            hide-details
                            @update:model-value="stage(item, $event)"
                            :disabled="readOnly || !can(project?.id, 'manage_workflow_whitelist')"
                            color="primary"
                            inline
                        >
                        </v-checkbox-btn>
                    </template>
                    <template #no-data>
                        <ListEmptyState
                            :search="search.trim()"
                            noun="workflows"
                            title="No workflows available"
                            text="The platform has no workflows installed that this project could run."
                            @clear-search="search = ''"
                        />
                    </template>
                </v-data-table>
            </div>
        </v-expand-transition>
    </v-col>
</template>

<script lang="ts" setup>
import { kaapanaIcons, projectIcons } from '@/utils/projectIcons'
import { ref, computed, onMounted, watch } from 'vue'
import { usePermissions } from '@/permissions/usePermissions'
import { aiiApiDelete, aiiApiGet, aiiApiPost, kaapanaBackendGetDags } from '@/common/services'
import SearchBar from '@/components/SearchBar.vue'
import ListEmptyState from '@/components/ListEmptyState.vue'
import FailureAlert from '@/components/FailureAlert.vue'
import { useViewDirty } from '@/composables/useViewDirty'
import { notify } from '@kyvg/vue3-notification'
import { notifyFailure } from '@/utils/notifyFailure'
import SectionHeader from '@/components/SectionHeader.vue'
import type { Software } from '@/common/types'

// ── Types ──────────────────────────────────────────────────────────────────

interface ProjectRef {
    id?: string
    name?: string
    is_archived?: boolean
}

interface Workflow {
    dag_name: string;
    inAii: boolean;
}

// ── Props & emits ──────────────────────────────────────────────────────────

const props = defineProps<{
    project: ProjectRef | null;
    expanded: boolean;
}>();

const emit = defineEmits<{
    (e: 'toggle', value: boolean): void;
}>();

// ── Permissions ────────────────────────────────────────────────────────────

const { can } = usePermissions()
const readOnly = computed(() => !!props.project?.is_archived)

// ── State ──────────────────────────────────────────────────────────────────

const search = ref('')
const workflows = ref<Workflow[]>([])
const isLoading = ref(false)
const loadError = ref<unknown>(null)
const isSaving = ref(false)
// pending: dag_name → desired inAii value (only changed ones)
const pending = ref<Record<string, boolean>>({});

// ── Table headers ──────────────────────────────────────────────────────────

const tableHeaders = [
    { title: '', key: 'icon', width: '40px' },
    { title: 'Workflow ID', key: 'dag_name' },
    {
        title: 'Allowed',
        key: 'inAii',
        width: '80px',
        align: 'center' as const,
        cellProps: ({ item }: { item: Workflow }) => ({
            class: isPending(item.dag_name) ? 'pm-pending' : '',
        }),
    },
]

// ── Computed ───────────────────────────────────────────────────────────────

const filteredWorkflows = computed(() => {
    const q = search.value.trim().toLowerCase();
    if (!q) return workflows.value;
    return workflows.value.filter(w =>
        w.dag_name?.toLowerCase().includes(q)
    );
});

const pendingCount = computed(() => Object.keys(pending.value).length)
useViewDirty(computed(() => pendingCount.value > 0))

// ── Pending changes helpers ────────────────────────────────────────────────

const effectiveInAii = (workflow: Workflow): boolean =>
    pending.value[workflow.dag_name] !== undefined
        ? pending.value[workflow.dag_name]
        : workflow.inAii;

const isPending = (dagName: string): boolean => dagName in pending.value;

const stage = (workflow: Workflow, value: boolean) => {
    if (value === workflow.inAii) {
        const { [workflow.dag_name]: _, ...rest } = pending.value;
        pending.value = rest;
    } else {
        pending.value = { ...pending.value, [workflow.dag_name]: value };
    }
};

const discardChanges = () => { pending.value = {}; };

const saveChanges = async () => {
    if (!props.project?.id) return;
    isSaving.value = true;

    const toAdd = Object.entries(pending.value).filter(([, allow]) => allow).map(([dag]) => ({ software_uuid: dag }));
    const toRemove = Object.entries(pending.value).filter(([, allow]) => !allow).map(([dag]) => ({ software_uuid: dag }));

    let saved = 0,
        failed = 0
    let lastError: unknown = null

    const apply = async (fn: () => Promise<void>, dags: string[], allow: boolean) => {
        try {
            await fn()
            dags.forEach((dag) => {
                const wf = workflows.value.find((w) => w.dag_name === dag)
                if (wf) wf.inAii = allow
            })
            pending.value = Object.fromEntries(
                Object.entries(pending.value).filter(([dag]) => !dags.includes(dag)),
            )
            saved += dags.length
        } catch (error) {
            lastError = error
            failed += dags.length
        }
    }

    const base = `projects/${props.project.id}/software-mappings`
    if (toAdd.length)
        await apply(
            () => aiiApiPost(base, toAdd),
            toAdd.map((x) => x.software_uuid),
            true,
        )
    if (toRemove.length)
        await apply(
            () => aiiApiDelete(base, {}, toRemove),
            toRemove.map((x) => x.software_uuid),
            false,
        )

    isSaving.value = false
    if (failed > 0) {
        notifyFailure('Workflows partly saved', `${saved} saved, ${failed} failed.`, lastError)
    } else {
        notify({ type: 'success', text: `${saved} workflow${saved !== 1 ? 's' : ''} updated.` })
    }
}

// ── Lifecycle ──────────────────────────────────────────────────────────────

onMounted(() => {
    if (props.project?.id) loadWorkflows();
});

watch(
    () => props.project?.id,
    (newId) => {
        if (newId) {
            pending.value = {};
            loadWorkflows();
        }
    }
);

// ── Data fetching ──────────────────────────────────────────────────────────

const loadWorkflows = async () => {
    if (!props.project?.id) return
    isLoading.value = true
    loadError.value = null
    try {
        const [whitelistMappings, allDags]: [Software[], string[]] = await Promise.all([
            aiiApiGet(`projects/${props.project.id}/software-mappings`),
            kaapanaBackendGetDags(true, true),
        ])
        const allowedWorkflowNames = new Set(
            (whitelistMappings ?? []).map((w) => w.software_uuid).filter(Boolean),
        )
        workflows.value = [...new Set(allDags ?? [])]
            .map((dag) => ({ dag_name: dag, inAii: allowedWorkflowNames.has(dag) }))
            .sort((a, b) => a.dag_name.localeCompare(b.dag_name))
    } catch (error) {
        loadError.value = error
    } finally {
        isLoading.value = false
    }
}
</script>
