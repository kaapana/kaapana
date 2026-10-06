<template>
    <v-col>
        <!-- ── Launch dialog ───────────────────────────────────────── -->
        <v-dialog v-model="isLaunchAppDialogOpen" max-width="600">
            <LaunchApplication
                v-if="selectedApplication"
                :extension="selectedApplication"
                :busy="isLaunching"
                @submit="onApplicationLaunched"
                @close="isLaunchAppDialogOpen = false"
            />
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

            <template v-if="can(project?.id, 'manage_applications_whitelist')" #actions>
                <v-chip v-if="pendingCount > 0" color="warning" variant="tonal" size="small">
                    {{ pendingCount }} unsaved
                </v-chip>
                <v-btn v-if="pendingCount > 0" size="small" variant="text" @click="discardChanges">Discard</v-btn>
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
        </SectionHeader>

        <!-- ── Expanded content ────────────────────────────────────── -->
        <v-expand-transition>
            <div v-if="expanded">
                <!-- search -->
                <SearchBar v-model="searchQuery" label="Search applications" />

                <!-- Loading skeleton -->
                <v-skeleton-loader v-if="isLoading" type="table" class="mt-4" />

                <FailureAlert
                    v-else-if="loadError"
                    title="Applications not loaded"
                    text="Could not load the applications that can be launched."
                    :error="loadError"
                    :retry="loadExtensions"
                />

                <!-- Applications table -->
                <v-data-table v-else-if="filteredExtensions.length > 0" :headers="extensionTableHeaders"
                    :items="filteredExtensions" :sort-by="[{ key: 'name', order: 'asc' }]" multi-sort class="mt-4">
                <template #item.icon>
                    <v-icon :icon="projectIcons.application" />
                </template>
                <template #item.name="{ item }">
                    <span class="font-weight-medium">{{ item.annotations['ui-visible-name'] }}</span>

                    <v-tooltip
                        v-if="item.annotations.documentation"
                        location="bottom"
                        text="Open the documentation in a new tab"
                    >
                        <template #activator="{ props }">
                            <v-btn
                                v-bind="props"
                                icon
                                variant="text"
                                size="small"
                                color="primary"
                                :href="getFullEndpoint('/docs/' + item.annotations.documentation)"
                                target="_blank"
                                rel="noopener noreferrer"
                                :aria-label="`Documentation for ${item.annotations['ui-visible-name']} (opens in a new tab)`"
                            >
                                <v-icon :icon="kaapanaIcons.help" />
                            </v-btn>
                        </template>
                    </v-tooltip>
                </template>
                <template #item.description="{ item }">
                    <v-tooltip location="bottom">
                        <template #activator="{ props }">
                            <span v-bind="props" class="d-inline-block text-truncate pm-description">
                                {{ item.description }}
                            </span>
                        </template>

                        <span>{{ item.description }}</span>
                    </v-tooltip>
                </template>
                <template #item.launch="{ item }">
                    <v-tooltip
                        text="This application is not whitelisted for this project. Contact your project admin."
                        :disabled="can(project?.id, 'launch_application', item.releaseName)"
                        location="top"
                    >
                        <template #activator="{ props }">
                            <span v-bind="props">
                                <v-btn
                                    color="primary"
                                    variant="text"
                                    :prepend-icon="kaapanaIcons.start"
                                    :loading="isLaunching && selectedApplication?.releaseName === item.releaseName"
                                    :disabled="isLaunching || !can(project?.id, 'launch_application', item.releaseName)"
                                    @click="onLaunchApplication(item)"
                                >
                                    Launch
                                </v-btn>
                            </span>
                        </template>
                    </v-tooltip>
                </template>
                <template #item.whitelistToggle="{ item }">
                    <v-checkbox-btn
                        :model-value="effectiveInWhitelist(item.releaseName)"
                        hide-details
                        @update:model-value="stage(item.releaseName, $event)"
                        :disabled="!can(project?.id, 'manage_applications_whitelist')"
                        color="primary"
                    />
                </template>
            </v-data-table>

                <!-- Empty state -->
                <v-sheet rounded v-else class="mt-4">
                    <v-container>
                        <v-row align="center" justify="center" no-gutters>
                            <v-icon :icon="kaapanaIcons.info" size="x-large" color="medium-emphasis"></v-icon>
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
import { kaapanaIcons, projectIcons } from '@/utils/projectIcons'
import { ref, computed, onMounted, watch } from 'vue'
import { usePermissions } from '@/permissions/usePermissions'
import { usePermissionsStore } from '@/permissions/permissions.store'
import { aiiApiPut, kubeHelmGet, kubeHelmPost } from '@/common/services'
import SearchBar from '@/components/SearchBar.vue'
import FailureAlert from '@/components/FailureAlert.vue'
import { useViewDirty } from '@/composables/useViewDirty'
import { notify } from '@kyvg/vue3-notification'
import { notifyFailure } from '@/utils/notifyFailure'
import SectionHeader from '@/components/SectionHeader.vue'
import LaunchApplication from '@/components/LaunchApplication.vue'

interface Extension {
    releaseName: string;
    annotations: {
        'ui-visible-name': string
        documentation?: string
    }
    description?: string
    version: string
    keywords: string[]
    // The backend reports a param-less extension as the literal string "null";
    // no config form then — install directly.
    extension_params?: Record<string, unknown> | 'null' | null
}

interface Props {
    project: { id?: string } | null;
    expanded: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: 'toggle', value: boolean): void
    (e: 'launched'): void
}>()

const { can } = usePermissions();
const permissionsStore = usePermissionsStore();

// ── State ──────────────────────────────────────────────────────────────────

const searchQuery = ref('')
const multiinstallableExtensions = ref<Extension[]>([])
const isLoading = ref(false)
const loadError = ref<unknown>(null)
const isSaving = ref(false)
// pending: releaseName → desired whitelist value (only changed items)
const pending = ref<Record<string, boolean>>({});

// Persisted whitelist from the store (source of truth after save)
const projectWhitelist = computed<string[]>(
    () => permissionsStore.whitelistByProject[props.project?.id ?? ''] ?? []
);

// ── Pending changes helpers ────────────────────────────────────────────────

const pendingCount = computed(() => Object.keys(pending.value).length)
useViewDirty(computed(() => pendingCount.value > 0))

const effectiveInWhitelist = (releaseName: string): boolean =>
    releaseName in pending.value
        ? pending.value[releaseName]
        : projectWhitelist.value.includes(releaseName);

const isPending = (releaseName: string): boolean => releaseName in pending.value;

const stage = (releaseName: string, value: boolean) => {
    const isCurrentlyAllowed = projectWhitelist.value.includes(releaseName);
    if (value === isCurrentlyAllowed) {
        const { [releaseName]: _, ...rest } = pending.value;
        pending.value = rest;
    } else {
        pending.value = { ...pending.value, [releaseName]: value };
    }
};

const discardChanges = () => { pending.value = {}; };

const saveChanges = async () => {
    if (!props.project?.id) return;
    isSaving.value = true;
    try {
        const finalWhitelist = projectWhitelist.value
            .filter(n => pending.value[n] !== false)
            .concat(
                Object.entries(pending.value)
                    .filter(([name, allow]) => allow && !projectWhitelist.value.includes(name))
                    .map(([name]) => name),
            )
        await aiiApiPut(
            `projects/${props.project.id}/multiinstallable-whitelist`,
            {},
            { app_names: finalWhitelist },
        )
        permissionsStore.whitelistByProject[props.project.id] = finalWhitelist
        pending.value = {}
        notify({ type: 'success', text: 'Application whitelist saved.' })
    } catch (error) {
        notifyFailure('Whitelist not saved', 'Could not save the application whitelist.', error)
    } finally {
        isSaving.value = false;
    }
};

// ── Launch dialog ──────────────────────────────────────────────────────────

const isLaunchAppDialogOpen = ref(false)
const isLaunching = ref(false)
const selectedApplication = ref<any>(null)

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

const hasParameters = (item: Extension) =>
    !!item.extension_params && item.extension_params !== 'null' && Object.keys(item.extension_params).length > 0

const onLaunchApplication = (item: Extension) => {
    selectedApplication.value = item;
    if (!hasParameters(item)) {
        onApplicationLaunched({ extension: item, values: {} })
        return
    }
    isLaunchAppDialogOpen.value = true;
};

const onApplicationLaunched = async ({ extension, values }: { extension: any; values: any }) => {
    const payload = {
        name: extension.releaseName,
        version: extension.version,
        keywords: extension.keywords,
        extension_params: values,
    }
    isLaunching.value = true
    try {
        await kubeHelmPost('helm-install-chart', payload)
        notify({ type: 'success', text: `${extension.annotations['ui-visible-name']} is starting.` })
        emit('launched')
        isLaunchAppDialogOpen.value = false
        selectedApplication.value = null
    } catch (error) {
        notifyFailure(
            'Application not launched',
            `Could not launch ${extension.annotations['ui-visible-name']}.`,
            error,
        )
    } finally {
        isLaunching.value = false
    }
}

const getFullEndpoint = (path: string) => {
    return `${window.location.origin}${path}`;
};

const loadExtensions = async () => {
    if (!props.project?.id) return
    loadError.value = null
    try {
        isLoading.value = true
        // Without the whitelist the "Allowed" column would show every application
        // as not allowed, and saving would replace the whitelist with only the
        // staged changes.
        const [extensions] = await Promise.all([
            kubeHelmGet('extensions'),
            permissionsStore.loadProjectWhitelist(props.project.id),
        ])
        const multiinstallable = extensions.filter((item: any) => item.multiinstallable === 'yes')
        
        multiinstallableExtensions.value = multiinstallable.filter((item: any) => item.installed === 'no');
    } catch (error) {
        loadError.value = error
    } finally {
        isLoading.value = false;
    }
};

// ── Lifecycle ──────────────────────────────────────────────────────────────

onMounted(() => {
    if (props.project?.id) loadExtensions();
});

watch(
    () => props.project?.id,
    (newId) => {
        if (newId) {
            pending.value = {};
            loadExtensions();
        }
    }
);

// ── Table headers ──────────────────────────────────────────────────────────

const extensionTableHeaders = [
    { title: '', key: 'icon', width: '40px' },
    { title: 'Name', key: 'name' },
    { title: 'Description', key: 'description' },
    { title: 'Launch', key: 'launch', width: '100px', align: 'center' as const },
    {
        title: 'Allowed',
        key: 'whitelistToggle',
        width: '80px',
        align: 'center' as const,
        cellProps: ({ item }: { item: Extension }) => ({
            class: isPending(item.releaseName) ? 'pm-pending' : '',
        }),
    },
]
</script>

<style scoped>
.pm-description {
    max-width: 28ch;
}
</style>
