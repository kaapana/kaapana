<template>
    <v-col>
        <!-- ── Snackbar ────────────────────────────────────────────── -->
        <v-snackbar v-model="isSnackbarVisible" :timeout="3000" location="top" :color="snackbarColor" elevation="2" closable>
            {{ snackbarMessage }}
        </v-snackbar>

        <!-- ── Launch dialog ───────────────────────────────────────── -->
        <v-dialog v-model="isLaunchAppDialogOpen" max-width="1000">
            <LaunchApplication v-if="selectedApplication" :extension="selectedApplication" @submit="onApplicationLaunched"
                @close="isLaunchAppDialogOpen = false" />
        </v-dialog>

        <!-- ── Section header ─────────────────────────────────────── -->
        <SectionHeader :expanded="expanded" @toggle="emit('toggle', $event)">
            <!-- LEFT TITLE -->
            <template #title>
                Multiinstallable Applications
            </template>

            <!-- OPTIONAL CHIP -->
            <template #meta>
                <v-chip v-if="filteredExtensions.length > 0" size="small" color="primary" variant="tonal">
                    {{ filteredExtensions.length }}
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
                <v-data-table v-else-if="filteredExtensions.length > 0" :headers="extensionTableHeaders"
                    :items="filteredExtensions" :sort-by="[{ key: 'name', order: 'asc' }]" multi-sort class="mt-4">
                <template #item.icon>
                    <td>
                        <v-icon icon="mdi-application-outline" />
                    </td>
                </template>
                <template #item.name="{ item }">
                    <td>
                        <span class="font-weight-medium">{{ item.annotations["ui-visible-name"] }}</span>

                        <!-- DOCUMENTATION LINK TOOLTIP -->
                        <v-tooltip location="bottom">
                            <template #activator="{ props }">
                                <a :href="getFullEndpoint('/docs/' + item.annotations.documentation)"
                                    target="_blank" v-bind="props">
                                    <v-icon class="cell-icon" color="primary">
                                        mdi-information
                                    </v-icon>
                                </a>
                            </template>

                            <span>Link to the documentation.</span>
                        </v-tooltip>

                    </td>
                </template>
                <template #item.description="{ item }">
                    <td>
                        <v-tooltip location="bottom">
                            <template #activator="{ props }">
                                <div v-bind="props">
                                    <span>
                                        {{ item.description.length > 28
                                            ? item.description.slice(0, 28) + "..."
                                            : item.description
                                            }}
                                    </span>
                                </div>
                            </template>

                            <span>{{ item.description }}</span>
                        </v-tooltip>
                    </td>
                </template>
                <template #item.launch="{ item }">
                    <td class="text-center">
                        <v-tooltip
                            text="This application is not whitelisted for this project. Contact your project admin."
                            :disabled="can(project?.id, 'launch_application', item.releaseName)"
                            location="top"
                        >
                            <template #activator="{ props }">
                                <span v-bind="props">
                                    <v-btn
                                        size="small"
                                        color="primary"
                                        variant="outlined"
                                        :disabled="!can(project?.id, 'launch_application', item.releaseName)"
                                        @click="onLaunchApplication(item)"
                                    >
                                        Launch
                                    </v-btn>
                                </span>
                            </template>
                        </v-tooltip>
                    </td>
                </template>
                <template #item.whitelistToggle="{ item }">
                    <td class="text-center">
                        <v-checkbox-btn
                            :model-value="projectWhitelist.includes(item.releaseName)"
                            hide-details
                            @update:model-value="updateWhitelist(item.releaseName, $event)"
                              :disabled="!can(project?.id, 'manage_applications_whitelist') || togglingWhitelist.includes(item.releaseName)"
                            color="success"
                        >
                        </v-checkbox-btn>
                    </td>
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
                                No multiinstallable applications found.
                            </div>
                        </v-row>
                    </v-container>
                </v-sheet>

            </div>
        </v-expand-transition>
    </v-col>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted, watch } from 'vue';
import { usePermissions } from '@/permissions/usePermissions';
import { usePermissionsStore } from '@/permissions/permissions.store';
import { aiiApiPut, kubeHelmGet, kubeHelmPost } from '@/common/services';
import SearchBar from '@/components/SearchBar.vue';
import SectionHeader from '@/components/SectionHeader.vue';
import LaunchApplication from '@/components/LaunchApplication.vue';

interface Extension {
    releaseName: string;
    annotations: {
        "ui-visible-name": string;
        documentation?: string;
    };
    description: string;
}

interface Props {
    project: { id?: string } | null;
    expanded: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: 'toggle', value: boolean): void;
    (e: 'whitelist-change', releaseName: string, isAllowed: boolean): void;
    (e: 'launch-application', item: Extension): void;
}>();

const { can } = usePermissions();
const permissionsStore = usePermissionsStore();

// ── State ──────────────────────────────────────────────────────────────────

const searchQuery = ref('');
const multiinstallableExtensions = ref<Extension[]>([]);
const installedExtensionsByReleaseName = ref<Record<string, any>>({});
const isLoading = ref(false);
const togglingWhitelist = ref<string[]>([]);

// Whitelist comes from the permissions store (loaded by project.vue on mount/refresh)
const projectWhitelist = computed<string[]>(
    () => permissionsStore.whitelistByProject[props.project?.id ?? ''] ?? []
);

// ── Launch dialog ──────────────────────────────────────────────────────────

const isLaunchAppDialogOpen = ref(false);
const selectedApplication = ref<any>(null);

// ── Snackbar ───────────────────────────────────────────────────────────────

const isSnackbarVisible = ref(false);
const snackbarMessage = ref('');
const snackbarColor = ref('info');

const showSnackbar = (message: string, color: string = 'info') => {
    snackbarMessage.value = message;
    snackbarColor.value = color;
    isSnackbarVisible.value = true;
};

// ── Computed ───────────────────────────────────────────────────────────────

const filteredExtensions = computed(() => {
    if (!searchQuery.value) return multiinstallableExtensions.value;
    const query = searchQuery.value.toLowerCase();
    return multiinstallableExtensions.value.filter((ext) =>
        ext.annotations["ui-visible-name"]?.toLowerCase().includes(query) ||
        ext.description?.toLowerCase().includes(query)
    );
});


// ── Methods ────────────────────────────────────────────────────────────────

const onLaunchApplication = (item: Extension) => {
    selectedApplication.value = item;
    isLaunchAppDialogOpen.value = true;
};

const onApplicationLaunched = async ({ extension, values }: { extension: any; values: any }) => {
const payload = {
      name: extension.releaseName,
      version: extension.version,
      keywords: extension.keywords,
      extension_params: values,
    };
    try {
        await kubeHelmPost('helm-install-chart', payload);
        showSnackbar(`Successfully launched ${extension.annotations['ui-visible-name']}`, 'success');
    } catch (error: any) {
        console.error('Failed to launch application:', error);
        const detail = error?.response?.data?.detail ?? error?.message ?? 'Unknown error';
        const isPermissionError = error?.response?.status === 403;
        showSnackbar(
            isPermissionError
                ? `Permission denied: ${detail}`
                : `Failed to launch ${extension.annotations['ui-visible-name']}: ${detail}`,
            'error'
        );
    }
    isLaunchAppDialogOpen.value = false;
    selectedApplication.value = null;
};

const getFullEndpoint = (path: string) => {
    return `${window.location.origin}${path}`;
};

const loadExtensions = async () => {
    if (!props.project?.id) return;
    try {
        isLoading.value = true;
        const extensions = await kubeHelmGet('extensions');
        const multiinstallable = extensions.filter((item: any) => item.multiinstallable === 'yes');
        
        multiinstallableExtensions.value = multiinstallable
            .filter((item: any) => item.installed === 'no')
            .map((item: any) => ({
                ...item
            }));

        installedExtensionsByReleaseName.value = multiinstallable
            .filter((item: any) => item.installed === 'yes')
            .reduce((map: any, item: any) => { map[item.releaseName] = item; return map; }, {});
    } catch (error) {
        console.error('Failed to load extensions:', error);
    } finally {
        isLoading.value = false;
    }
};

const updateWhitelist = async (releaseName: string, isAllowed: boolean) => {
    if (!props.project?.id) return;
    togglingWhitelist.value = [...togglingWhitelist.value, releaseName];
    try {
        const current = permissionsStore.whitelistByProject[props.project.id] ?? [];
        const updated = isAllowed
            ? [...current, releaseName]
            : current.filter(name => name !== releaseName);
        await aiiApiPut(`projects/${props.project.id}/multiinstallable-whitelist`, {}, { app_names: updated });
        permissionsStore.whitelistByProject[props.project.id] = updated;
    } catch (error) {
        console.error('Failed to update whitelist:', error);
    } finally {
        togglingWhitelist.value = togglingWhitelist.value.filter(name => name !== releaseName);
    }
};

// ── Lifecycle ──────────────────────────────────────────────────────────────

onMounted(() => {
    if (props.project?.id) loadExtensions();
});

watch(
    () => props.project?.id,
    (newId) => { if (newId) loadExtensions(); }
);

// ── Table headers ──────────────────────────────────────────────────────────

const extensionTableHeaders = [
    { title: '', key: 'icon', width: '40px' },
    { title: 'Name', key: 'name' },
    { title: 'Description', key: 'description' },
    { title: 'Launch', key: 'launch', width: '100px', align: 'center' as const },
    { title: 'Allowed', key: 'whitelistToggle', width: '80px', align: 'center' as const },
];
</script>
