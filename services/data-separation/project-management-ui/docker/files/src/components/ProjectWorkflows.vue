<template>
    <v-col>
        <!-- ── Snackbar ────────────────────────────────────────────── -->
        <v-snackbar v-model="isSnackbarVisible" :timeout="3000" location="top" :color="snackbarColor" elevation="2" closable>
            {{ snackbarMessage }}
        </v-snackbar>

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
                        {{ pendingCount }} unsaved
                    </v-chip>
                    <v-btn
                        v-if="pendingCount > 0"
                        size="small"
                        variant="text"
                        @click="discardChanges"
                    >
                        Discard
                    </v-btn>
                    <v-btn
                        :disabled="pendingCount === 0 || isSaving"
                        :loading="isSaving"
                        size="small"
                        color="primary"
                        variant="outlined"
                        prepend-icon="mdi-content-save"
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
                <SearchBar v-model="search" placeholder="Search workflows..." />

                <!-- Loading skeleton -->
                <v-skeleton-loader v-if="isLoading" type="table" class="mt-4" />

                <!-- Workflow table -->
                <v-data-table
                    v-else-if="filteredWorkflows.length > 0"
                    :headers="tableHeaders"
                    :items="filteredWorkflows"
                    :sort-by="[{ key: 'dag_name', order: 'asc' }]"
                    multi-sort
                    class="mt-4"
                >
                    <template #item.icon>
                        <td>
                            <v-icon icon="mdi-gamepad-variant" />
                        </td>
                    </template>

                    <template #item.dag_name="{ item }">
                        <td>
                            <span class="font-weight-medium" style="font-family: monospace">{{ item.dag_name }}</span>
                        </td>
                    </template>

                    <template #item.inAii="{ item }">
                        <td class="text-center" :class="isPending(item.dag_name) ? 'bg-warning-lighten-4' : ''">
                            <v-checkbox-btn
                                :model-value="effectiveInAii(item)"
                                hide-details
                                @update:model-value="stage(item, $event)"
                                :disabled="!can(project?.id, 'manage_workflow_whitelist')"
                                color="success"
                                inline
                            >
                            </v-checkbox-btn>
                        </td>
                    </template>
                </v-data-table>

                <!-- Empty state -->
                <v-sheet v-else rounded class="mt-4">
                    <v-container class="text-center py-8">
                        <v-icon icon="mdi-gamepad-variant-outline" size="x-large" color="medium-emphasis" />
                        <div class="text-subtitle-1 text-medium-emphasis mt-4">
                            No workflows available
                        </div>
                    </v-container>
                </v-sheet>
            </div>
        </v-expand-transition>
    </v-col>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted, watch } from 'vue';
import { usePermissions } from '@/permissions/usePermissions';
import { aiiApiDelete, aiiApiGet, aiiApiPost, kaapanaBackendGetDags } from '@/common/services';
import SearchBar from '@/components/SearchBar.vue';
import SectionHeader from '@/components/SectionHeader.vue';
import type { Software } from '@/common/types';

// ── Types ──────────────────────────────────────────────────────────────────

interface ProjectRef {
    id?: string;
    name?: string;
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

const { can } = usePermissions();

// ── State ──────────────────────────────────────────────────────────────────

const search = ref('');
const workflows = ref<Workflow[]>([]);
const isLoading = ref(false);
const isSaving = ref(false);
// pending: dag_name → desired inAii value (only changed ones)
const pending = ref<Record<string, boolean>>({});

// ── Snackbar ───────────────────────────────────────────────────────────────

const isSnackbarVisible = ref(false);
const snackbarMessage = ref('');
const snackbarColor = ref('info');

const showSnackbar = (message: string, color: string = 'info') => {
    snackbarMessage.value = message;
    snackbarColor.value = color;
    isSnackbarVisible.value = true;
};

// ── Table headers ──────────────────────────────────────────────────────────

const tableHeaders = [
    { title: '', key: 'icon', width: '40px' },
    { title: 'Workflow ID', key: 'dag_name' },
    { title: 'Allowed', key: 'inAii', width: '80px', align: 'center' as const },
];

// ── Computed ───────────────────────────────────────────────────────────────

const filteredWorkflows = computed(() => {
    const q = search.value.trim().toLowerCase();
    if (!q) return workflows.value;
    return workflows.value.filter(w =>
        w.dag_name?.toLowerCase().includes(q)
    );
});

const pendingCount = computed(() => Object.keys(pending.value).length);

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
    let saved = 0, failed = 0;
    for (const [dagName, allow] of Object.entries(pending.value)) {
        try {
            if (allow) {
                await aiiApiPost(`projects/${props.project.id}/software-mappings`, [{ software_uuid: dagName }]);
            } else {
                await aiiApiDelete(`projects/${props.project.id}/software-mappings`, {}, [{ software_uuid: dagName }]);
            }
            // Update committed state
            const wf = workflows.value.find(w => w.dag_name === dagName);
            if (wf) wf.inAii = allow;
            saved++;
        } catch (error: any) {
            console.error(`Failed to update ${dagName}:`, error);
            failed++;
        }
    }
    pending.value = {};
    isSaving.value = false;
    if (failed > 0) {
        showSnackbar(`${saved} saved, ${failed} failed.`, 'warning');
    } else {
        showSnackbar(`${saved} workflow${saved !== 1 ? 's' : ''} updated.`, 'success');
    }
};

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
    if (!props.project?.id) return;
    isLoading.value = true;
    const allWorkflows: Workflow[] = [];
    let allowedWorkflowNames = new Set<string>();

    try {
        // 1. Load AII software mappings for the project (whitelist)
        if (props.project?.id) {
            try {
                const aiiWorkflows: Software[] = await aiiApiGet(
                    `projects/${props.project.id}/software-mappings`
                );
                allowedWorkflowNames = new Set(
                    (aiiWorkflows ?? []).map(w => w.software_uuid).filter(Boolean) as string[]
                );
            } catch (error) {
                console.error('Failed to load AII workflows:', error);
            }
        }

        // 2. Load from kaapana-backend
        try {
            const kaapanaDags: string[] = await kaapanaBackendGetDags(true, true);
            for (const dag of (kaapanaDags ?? [])) {
                allWorkflows.push({
                    dag_name: dag,
                    inAii: allowedWorkflowNames.has(dag),
                });
            }
        } catch (error) {
            console.error('Failed to load kaapana-backend DAGs:', error);
        }

        // Remove duplicates by dag_name and sort
        const seen = new Set<string>();
        const uniqueWorkflows = allWorkflows.filter(w => {
            if (seen.has(w.dag_name)) return false;
            seen.add(w.dag_name);
            return true;
        });
        workflows.value = uniqueWorkflows.sort((a, b) =>
            a.dag_name.localeCompare(b.dag_name)
        );
    } catch (error) {
        console.error('Failed to load workflows:', error);
    } finally {
        isLoading.value = false;
    }
};
</script>