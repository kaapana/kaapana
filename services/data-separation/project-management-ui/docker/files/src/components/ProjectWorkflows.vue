<template>
    <v-col>
        <!-- ── Snackbar ────────────────────────────────────────────── -->
        <v-snackbar v-model="isSnackbarVisible" :timeout="10000" location="top" :color="snackbarColor" elevation="2">
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
                <!-- Add Workflow button removed - showing all workflows from all sources -->
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
                            <span class="font-weight-medium">{{ item.dag_name }}</span>
                        </td>
                    </template>

                    <template #item.inAii="{ item }">
                        <td class="text-center">
                            <v-checkbox-btn
                                :model-value="item.inAii"
                                hide-details
                                @update:model-value="toggleWorkflow(item)"
                                :disabled="!can(project?.id, 'manage_project_workflows')"
                                color="success"
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

// ── Toggle handler ─────────────────────────────────────────────────────────

const toggleWorkflow = async (workflow: Workflow) => {
  if (!can(props.project?.id, 'manage_project_workflows')) return;
    // Optimistically update the UI
    const wasAllowed = workflow.inAii;
    workflow.inAii = !wasAllowed;
    
    try {
        if (wasAllowed) {
            // Remove from whitelist
            await confirmRemoveWorkflow(workflow);
        } else {
            // Add to whitelist
            await addWorkflowToWhitelist(workflow);
        }
    } catch (error: any) {
        // Revert on error
        console.error('Toggle failed, reverting:', error);
        workflow.inAii = wasAllowed;
        showSnackbar(`Failed to update workflow: ${error?.response?.data || 'Unknown error'}`, 'error');
    }
};

// ── Lifecycle ──────────────────────────────────────────────────────────────

onMounted(() => {
    loadWorkflows();
});

watch(
    () => props.project?.id,
    () => { loadWorkflows(); }
);

const confirmRemoveWorkflow = async (workflow: Workflow) => {
    if (!workflow || !props.project?.id) return;
    try {
        await aiiApiDelete(
            `projects/${props.project.id}/software-mappings`,
            {},
            [{ software_uuid: workflow.dag_name }]
        );
    } catch (error) {
        console.error('Failed to remove workflow from whitelist:', error);
        throw error;
    }
};

const addWorkflowToWhitelist = async (workflow: Workflow) => {
    if (!props.project?.id) return;
    try {
        await aiiApiPost(
            `projects/${props.project.id}/software-mappings`,
            [{ software_uuid: workflow.dag_name }]
        );
    } catch (error) {
        console.error('Failed to add workflow to whitelist:', error);
        throw error;
    }
};

// ── Data fetching ──────────────────────────────────────────────────────────

const loadWorkflows = async () => {
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