<template>
    <v-col>
        <!-- ── Section header ─────────────────────────────────────── -->
        <SectionHeader :expanded="expanded" @toggle="emit('toggle', $event)">
            <!-- LEFT TITLE -->
            <template #title>
                Active Project Applications
            </template>

            <!-- OPTIONAL CHIP -->
            <template #meta>
                <v-chip v-if="filteredActiveApplications.length > 0" size="small" color="primary" variant="tonal">
                    {{ filteredActiveApplications.length }}
                </v-chip>
            </template>
        </SectionHeader>

        <!-- ── Expanded content ────────────────────────────────────── -->
        <v-expand-transition>
            <div v-if="expanded">
                <!-- search -->
                <SearchBar v-model="searchQuery" label="Search applications" />

                <FailureAlert
                    v-if="loadError"
                    title="Applications not loaded"
                    text="Could not load the applications running in this project."
                    :error="loadError"
                    :retry="loadActiveApplications"
                />

                <!-- Applications table -->
                <v-data-table
                    v-else
                    :loading="isLoading"
                    loading-text="Loading applications…"
                    :items-per-page="-1"
                    hide-default-footer
                    :headers="activeAppTableHeaders"
                    :items="filteredActiveApplications"
                    :sort-by="[{ key: 'name', order: 'asc' }]"
                    multi-sort
                    class="mt-4"
                >
                    <template #item.icon>
                        <v-icon :icon="projectIcons.application" />
                    </template>
                    <template #item.details="{ item }">
                        <v-tooltip
                            v-if="item.values && Object.keys(item.values).length > 0"
                            text="Show parameters"
                            location="top"
                        >
                            <template #activator="{ props }">
                                <v-btn
                                    v-bind="props"
                                    :icon="kaapanaIcons.info"
                                    :aria-label="`Parameters of ${item.annotations['kaapana.ai/display-name']}`"
                                    color="primary"
                                    variant="text"
                                    @click="showParameters(item)"
                                />
                            </template>
                        </v-tooltip>
                    </template>
                    <template #item.links="{ item }">
                        <div class="d-flex justify-center ga-2">
                            <v-tooltip
                                v-for="path in item.paths"
                                :key="path"
                                text="Open in a new tab"
                                location="top"
                            >
                                <template #activator="{ props }">
                                    <v-btn
                                        v-bind="props"
                                        :icon="kaapanaIcons.externalLink"
                                        :href="getFullEndpoint(path)"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        :aria-label="`Open ${item.annotations['kaapana.ai/display-name']} in a new tab`"
                                        color="primary"
                                        variant="text"
                                    />
                                </template>
                            </v-tooltip>
                        </div>
                    </template>
                    <template #item.uninstall="{ item }">
                        <v-tooltip
                            :text="
                                can(project?.id, 'delete_active_apps', item.release_name)
                                    ? 'Uninstall application'
                                    : 'Not whitelisted for this project. Only admins can uninstall this.'
                            "
                            location="top"
                        >
                            <template #activator="{ props }">
                                <span v-bind="props">
                                    <v-btn
                                        density="default"
                                        :icon="kaapanaIcons.delete"
                                        :aria-label="`Uninstall ${item.annotations['kaapana.ai/display-name']}`"
                                        :loading="busyRelease === item.release_name"
                                        color="error"
                                        variant="text"
                                        :disabled="
                                            !!busyRelease || !can(project?.id, 'delete_active_apps', item.release_name)
                                        "
                                        @click="onConfirmUninstall(item)"
                                    />
                                </span>
                            </template>
                        </v-tooltip>
                    </template>
                    <template #no-data>
                        <ListEmptyState
                            :search="searchQuery"
                            noun="applications"
                            title="No applications running"
                            text="Applications launched in this project appear here."
                            @clear-search="searchQuery = ''"
                        />
                    </template>
                </v-data-table>
            </div>
        </v-expand-transition>

        <!-- Parameters Dialog -->
        <ApplicationParametersDialog
            v-model="parametersDialog"
            :application="selectedApplication"
            @close="parametersDialog = false"
        />

        <ConfirmDialog
            v-model="confirmOpen"
            :color="confirmation.color"
            :title="confirmation.title"
            :text="confirmation.text"
            :confirm-text="confirmation.confirmText"
            @confirm="runConfirmed"
        />
    </v-col>
</template>

<script lang="ts" setup>
import { kaapanaIcons, projectIcons } from '@/utils/projectIcons'
import { ref, computed, onMounted, watch } from 'vue'
import { kubeHelmGet } from '@/common/services'
import SearchBar from '@/components/SearchBar.vue'
import ListEmptyState from '@/components/ListEmptyState.vue'
import SectionHeader from '@/components/SectionHeader.vue'
import ApplicationParametersDialog from './ApplicationParametersDialog.vue'
import { ConfirmDialog } from '@kaapana/base-ui'
import { useConfirmation } from '@/composables/useConfirmation'
import FailureAlert from '@/components/FailureAlert.vue'
import { usePermissions } from '@/permissions/usePermissions'

interface ActiveApplication {
    release_name: string;
    annotations: {
        "kaapana.ai/display-name": string;
    };
    paths: string[];
    project: string;
    values?: Record<string, any>;
}

interface InstalledExtension {
    helmStatus?: string;
}

interface Props {
    project: { id?: string } | null
    expanded: boolean
    busyRelease?: string | null
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: 'toggle', value: boolean): void;
  (e: 'confirm-uninstall', app: ActiveApplication): void;
}>();

const { can } = usePermissions()
const { confirmOpen, confirmation, ask, runConfirmed } = useConfirmation()

// ── State ──────────────────────────────────────────────────────────────────

const searchQuery = ref('')
const activeApplications = ref<ActiveApplication[]>([])
const installedExtensionsByReleaseName = ref<Record<string, InstalledExtension>>({})
const isLoading = ref(false)
const loadError = ref<unknown>(null)
const parametersDialog = ref(false)
const selectedApplication = ref<ActiveApplication | null>(null)

// ── Computed ───────────────────────────────────────────────────────────────

const filteredActiveApplications = computed(() => {
    if (!searchQuery.value) return activeApplications.value;
    const query = searchQuery.value.toLowerCase();
    return activeApplications.value.filter((app) =>
        app.annotations["kaapana.ai/display-name"]?.toLowerCase().includes(query)
    );
});

// ── Methods ────────────────────────────────────────────────────────────────

const onConfirmUninstall = (app: ActiveApplication) => {
    ask({
        color: 'error',
        title: `Uninstall "${app.annotations['kaapana.ai/display-name']}"?`,
        text:
            'The application is stopped and removed from the project. Files it synchronized to the ' +
            "project's storage stay; anything else inside it is lost. The application can be " +
            'launched again later.',
        confirmText: 'Uninstall application',
        action: () => emit('confirm-uninstall', app),
    })
}

const getFullEndpoint = (path: string): string => {
    return `${window.location.origin}${path}`;
};

const showParameters = (app: ActiveApplication) => {
    selectedApplication.value = app;
    parametersDialog.value = true;
};

const loadActiveApplications = async () => {
    if (!props.project?.id) return
    loadError.value = null
    try {
        isLoading.value = true;
        const allApps = await kubeHelmGet('active-applications');
        activeApplications.value = allApps.filter((item: any) => item.project === props.project!.id);
        
        // Load installed extensions for status info
        const extensions = await kubeHelmGet('extensions');
        const multiinstallable = extensions.filter((item: any) => item.multiinstallable === 'yes');
        installedExtensionsByReleaseName.value = multiinstallable
            .filter((item: any) => item.installed === 'yes')
            .reduce((map: any, item: any) => { map[item.releaseName] = item; return map; }, {});
    } catch (error) {
        loadError.value = error
    } finally {
        isLoading.value = false;
    }
};

// ── Lifecycle ──────────────────────────────────────────────────────────────

onMounted(() => {
    if (props.project?.id) loadActiveApplications();
});

watch(
    () => props.project?.id,
    (newId) => { if (newId) loadActiveApplications(); }
);

// ── Table headers ──────────────────────────────────────────────────────────

const activeAppTableHeaders = [
    { title: '', key: 'icon', width: '40px', sortable: false },
    {
        title: 'Name',
        key: 'name',
        value: (app: ActiveApplication) => app.annotations['kaapana.ai/display-name'],
    },
    {
        title: 'Status',
        key: 'status',
        value: (app: ActiveApplication) =>
            installedExtensionsByReleaseName.value[app.release_name]?.helmStatus ?? '',
    },
    { title: 'Details', key: 'details', align: 'center' as const, sortable: false },
    { title: 'Links', key: 'links', align: 'center' as const, sortable: false },
    { title: 'Actions', key: 'uninstall', align: 'center' as const, width: '60px', sortable: false },
]
</script>
