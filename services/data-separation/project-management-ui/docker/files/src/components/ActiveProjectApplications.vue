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
                <SearchBar v-model="searchQuery" placeholder="Search applications..." />

                <!-- Loading skeleton -->
                <v-skeleton-loader v-if="isLoading" type="table" class="mt-4" />

                <!-- Applications table -->
                <v-data-table v-else-if="filteredActiveApplications.length > 0"
                    :headers="activeAppTableHeaders"
                    :items="filteredActiveApplications"
                    :sort-by="[{ key: 'name', order: 'asc' }]"
                    multi-sort
                    class="mt-4"
                >
                <template #item="{ item }">
                    <tr>
                        <td><v-icon>mdi-application-outline</v-icon></td>
                        <td>{{ item.annotations["kaapana.ai/display-name"] }}</td>
                        <td>{{ installedExtensionsByReleaseName[item.release_name]?.helmStatus }}</td>
                        <td class="text-center">
                            <v-btn
                                v-if="item.values && Object.keys(item.values).length > 0"
                                
                                icon="mdi-information"
                                color="primary"
                                variant="text"
                                @click="showParameters(item)"
                            />
                        </td>
                        <td class="text-center">
                            <div class="d-flex justify-center ga-2">
                                <a
                                    v-for="path in item.paths"
                                    :key="path"
                                    :href="getFullEndpoint(path)"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    <v-icon size="large" color="primary">mdi-open-in-new</v-icon>
                                </a>
                            </div>
                        </td>
                        <td class="text-center" v-if="userHasAdminAccess">
                            <v-btn
                                density="default"
                                icon="mdi-trash-can"
                                color="error"
                                variant="text"
                                @click="onConfirmUninstall(item)"
                            />
                        </td>
                    </tr>
                </template>
            </v-data-table>

                <!-- Empty state -->
                <v-sheet rounded v-else class="mt-4">
                    <v-container>
                        <v-row align="center" justify="center" no-gutters>
                            <v-icon icon="mdi-information" size="x-large" class="large-font"></v-icon>
                        </v-row>
                        <v-row align="center" justify="center" no-gutters class="py-6">
                            <div class="text-subtitle-1 font-weight-light text-center">
                                No active applications found for this project.
                            </div>
                        </v-row>
                    </v-container>
                </v-sheet>

            </div>
        </v-expand-transition>

        <!-- Parameters Dialog -->
        <ApplicationParametersDialog
            v-model="parametersDialog"
            :application="selectedApplication"
            @close="parametersDialog = false"
        />

        <!-- Uninstall Confirmation Dialog -->
        <v-dialog v-model="uninstallDialog" max-width="600px">
            <v-card>
                <v-card-title class="bg-error text-white">
                    <span class="text-h5">Uninstall Application</span>
                </v-card-title>
                <v-card-text>
                    <v-alert type="warning" variant="tonal" class="mb-0">
                        Are you sure you want to uninstall <strong>{{ selectedApplication?.annotations["kaapana.ai/display-name"] }}</strong>?
                        This action cannot be undone.
                    </v-alert>
                </v-card-text>
                <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn color="primary" variant="text" @click="uninstallDialog = false">
                        Cancel
                    </v-btn>
                    <v-btn color="error" variant="text" @click="confirmUninstall">
                        Uninstall
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>
    </v-col>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted, watch } from 'vue';
import { kubeHelmGet } from '@/common/services';
import SearchBar from '@/components/SearchBar.vue';
import SectionHeader from '@/components/SectionHeader.vue';
import ApplicationParametersDialog from './ApplicationParametersDialog.vue';

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
    project: { id?: string } | null;
    expanded: boolean;
    userHasAdminAccess: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: 'toggle', value: boolean): void;
    (e: 'confirm-uninstall', app: ActiveApplication): void;
}>();

// ── State ──────────────────────────────────────────────────────────────────

const searchQuery = ref('');
const activeApplications = ref<ActiveApplication[]>([]);
const installedExtensionsByReleaseName = ref<Record<string, InstalledExtension>>({});
const isLoading = ref(false);
const parametersDialog = ref(false);
const selectedApplication = ref<ActiveApplication | null>(null);
const uninstallDialog = ref(false);

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
    selectedApplication.value = app;
    uninstallDialog.value = true;
};

const confirmUninstall = () => {
    if (selectedApplication.value) {
        emit('confirm-uninstall', selectedApplication.value);
        uninstallDialog.value = false;
    }
};

const getFullEndpoint = (path: string): string => {
    return `${window.location.origin}${path}`;
};

const showParameters = (app: ActiveApplication) => {
    selectedApplication.value = app;
    parametersDialog.value = true;
};

const loadActiveApplications = async () => {
    if (!props.project?.id) return;
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
        console.error('Failed to load active applications:', error);
    } finally {
        isLoading.value = false;
    }
};

// ── Lifecycle ──────────────────────────────────────────────────────────────

onMounted(() => {
    if (props.project?.id) {
        loadActiveApplications();
    }
});

watch(
    () => props.project?.id,
    (newId) => {
        if (newId) {
            loadActiveApplications();
        }
    }
);

// ── Table headers ──────────────────────────────────────────────────────────

const activeAppTableHeaders = [
    { title: '', key: 'icon', width: '40px' },
    { title: 'Name', key: 'name' },
    { title: 'Status', key: 'status' },
    { title: 'Details', key: 'details', align: 'center' as const },
    { title: 'Links', key: 'links', align: 'center' as const },
    { title: 'Actions', key: 'uninstall', align: 'center' as const, width: '60px' },
];
</script>
