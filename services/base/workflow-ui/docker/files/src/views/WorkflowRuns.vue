<template>
	<v-container fluid>
		<v-container class="pad-lg">
			<!-- Header -->
			<v-row class="mb-4">
				<v-col cols="12">
					<div class="d-flex align-center justify-space-between mb-4">
						<h1 class="text-h5 mb-0">Workflow Runs</h1>

						<div class="d-flex align-center gap-2">
							<v-btn small variant="text" color="primary" aria-label="info" @click="showInfo = true">
								<v-icon size="32">mdi-information</v-icon>
							</v-btn>

							<v-btn small color="primary" aria-label="refresh" @click="loadData" :loading="isRefreshing">
								<v-icon left size="18">mdi-refresh</v-icon>
								REFRESH
							</v-btn>
						</div>
					</div>

					<!-- Search bar component -->
					<SearchBar :runs="runs" @update:filters="onSearchUpdate" @apply:filtered="onSearchApply" />
				</v-col>
			</v-row>

			<v-row class="mb-2">
				<v-col cols="12">
					<!-- Statistics Header -->
					<v-card v-if="!loading">
						<v-card-text class="py-3">
							<div class="d-flex align-center justify-space-between flex-wrap gap-3">
								<!-- Total count -->
								<div class="d-flex align-center gap-2">
									<v-icon size="20" color="primary">mdi-counter</v-icon>
									<span class="text-body-2 font-weight-medium">
										Total: <strong>{{ runs.length }}</strong> runs
									</span>
									<span class="text-caption text-medium-emphasis"
										v-if="sortedFilteredRuns.length !== runs.length">
										({{ sortedFilteredRuns.length }} filtered)
									</span>
								</div>

								<!-- Status breakdown -->
								<div class="d-flex align-center gap-2 flex-wrap">
									<span class="text-caption text-medium-emphasis mr-1">Status:</span>
									<v-chip v-for="(count, status) in statusStatistics" :key="status" size="small"
										:color="statusColor(status)"
										:variant="isStatusFiltered(status) ? 'flat' : 'outlined'"
										@click="toggleStatusFilter(status)" class="stats-chip">
										<span class="font-weight-medium">{{ status }}</span>
										<v-divider vertical class="mx-1" />
										<span>{{ count }}</span>
									</v-chip>
								</div>
							</div>
						</v-card-text>
					</v-card>
				</v-col>
			</v-row>

			<!-- Info dialog -->
			<v-dialog v-model="showInfo" max-width="600">
				<v-card>
					<v-card-title>About the Workflow Runs page</v-card-title>
					<v-card-text>
						This page displays all workflow runs in a single table. Use the search field to build query
						filters
						(status:, workflow:, id:). Runs are always sorted by creation date (newest first). You can
						cancel running
						workflows or retry failed ones.
					</v-card-text>
					<v-card-actions>
						<v-spacer />
						<v-btn text @click="showInfo = false">Close</v-btn>
					</v-card-actions>
				</v-card>
			</v-dialog>

			<v-row>
				<!-- WORKFLOW RUNS TABLE -->
				<v-col cols="12">
					<!-- Loading state -->
					<v-row v-if="loading" class="d-flex justify-center align-center" style="min-height: 300px;">
						<v-progress-circular indeterminate color="primary" size="64" />
					</v-row>

					<!-- Error state -->
					<v-row v-else-if="error" class="d-flex justify-center">
						<v-col cols="12">
							<v-alert type="error" prominent>{{ error }}</v-alert>
						</v-col>
					</v-row>

					<!-- Empty state -->
					<v-row v-else-if="runs.length === 0" class="d-flex justify-center">
						<v-col cols="12">
							<v-alert type="info" prominent>No workflow runs available.</v-alert>
						</v-col>
					</v-row>

					<!-- Runs table -->
					<v-data-table v-else :headers="tableHeaders" :items="sortedFilteredRuns" density="comfortable"
						class="workflow-runs-table" :items-per-page="25" :items-per-page-options="[10, 25, 50, 100]">
						<template #item="{ item }">
							<WorkflowRunRow :run="item" @cancel="cancelRun" @retry="retryRun" />
						</template>
					</v-data-table>

					<!-- Filtered state - runs exist but none match filters -->
					<v-row v-if="!loading && runs.length > 0 && sortedFilteredRuns.length === 0"
						class="d-flex justify-center mt-4">
						<v-col cols="12">
							<v-alert type="info" prominent>No workflow runs match your filters.</v-alert>
						</v-col>
					</v-row>
				</v-col>
			</v-row>
		</v-container>

		<!-- Snackbar for notifications -->
		<v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="4000" location="top right">
			{{ snackbar.message }}
			<template #actions>
				<v-btn variant="text" @click="snackbar.show = false">
					Close
				</v-btn>
			</template>
		</v-snackbar>
	</v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import SearchBar from '@/components/SearchBar.vue'
import WorkflowRunRow from '@/components/WorkflowRun.vue'
import { workflowRunsApi } from '@/api/workflowRuns'
import type { WorkflowRun } from '@/types/schemas'
import { statusColor } from '@/utils/status'

// --- STATE ---
const runs = ref<WorkflowRun[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

// UI state
const showInfo = ref(false)
const isRefreshing = ref(false)
const textSearchQuery = ref('')
const valueSearchQuery = ref('')

const snackbar = ref({
	show: false,
	message: '',
	color: 'success'
})

function showSnackbar(message: string, color: string = 'success') {
	snackbar.value = {
		show: true,
		message,
		color
	}
}

// Handlers for SearchBar component
function onSearchUpdate(payload: { appliedFilters: Array<{ field: string; value: string }>; text: string }) {
	appliedFilters.value = Array.isArray(payload?.appliedFilters) ? payload.appliedFilters.slice() : []
	textSearchQuery.value = payload?.text || ''
}

// Store the filtered results from SearchBar
const searchBarFiltered = ref<WorkflowRun[]>([])

function onSearchApply(filtered: WorkflowRun[]) {
	// Store the filtered and sorted results from SearchBar
	searchBarFiltered.value = filtered
}

// --- FILTER BUILDER STATE ---
interface FilterValue {
	field: string | null
	value: string | null
}

interface AppliedFilter {
	field: string
	value: string
}

const buildingFilter = ref<FilterValue>({
	field: null,
	value: null
})

const appliedFilters = ref<AppliedFilter[]>([])

const tableHeaders: any = [
	{ title: 'Status', key: 'lifecycle_status', sortable: false, width: '130px', align: 'center' },
	{ title: 'Workflow', key: 'workflow_title', sortable: false, width: '250px', align: 'start' },
	{ title: 'Created At', key: 'created_at', sortable: false, width: '180px', align: 'center' },
	{ title: 'Updated At', key: 'updated_at', sortable: false, width: '180px', align: 'center' },
	{ title: 'External ID', key: 'external_id', sortable: false, width: '200px', align: 'start' },
	{ title: 'Actions', key: 'actions', sortable: false, width: '120px', align: 'center' },
]

// --- LOAD DATA ---
async function loadData() {
	if (isRefreshing.value) return

	loading.value = true
	isRefreshing.value = true
	error.value = null
	try {
		const runsData = await workflowRunsApi.getAll()
		runs.value = Array.isArray(runsData) ? runsData : []
	} catch (err) {
		console.error(err)
		error.value = 'Failed to fetch workflow runs.'
		runs.value = []
	} finally {
		loading.value = false
		isRefreshing.value = false
	}
}

onMounted(loadData)

// --- FILTER AND SORT ---
// Use SearchBar's filtered results if available, otherwise show all runs
const sortedFilteredRuns = computed(() => {
	// If SearchBar has emitted filtered results, use those (includes sorting)
	if (searchBarFiltered.value.length > 0 || appliedFilters.value.length > 0 || textSearchQuery.value) {
		return searchBarFiltered.value
	}

	// Otherwise show all runs, sorted by created_at descending
	const sorted = [...runs.value]
	sorted.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
	return sorted
})

// --- STATISTICS ---
const statusStatistics = computed(() => {
	const stats: Record<string, number> = {}

	for (const run of runs.value) {
		const status = run.lifecycle_status
		stats[status] = (stats[status] || 0) + 1
	}

	// Sort by predefined order
	const order = ['Running', 'Pending', 'Scheduled', 'Created', 'Completed', 'Error', 'Canceled']
	const sorted: Record<string, number> = {}

	for (const status of order) {
		if (stats[status]) {
			sorted[status] = stats[status]
		}
	}

	return sorted
})

// Check if a status is currently filtered
function isStatusFiltered(status: string): boolean {
	return appliedFilters.value.some(f =>
		f.field === 'status' &&
		f.value.toLowerCase() === status.toLowerCase()
	)
}

// Toggle status filter
function toggleStatusFilter(status: string) {
	const existingIndex = appliedFilters.value.findIndex(f =>
		f.field === 'status' &&
		f.value.toLowerCase() === status.toLowerCase()
	)

	if (existingIndex !== -1) {
		// Remove the filter
		appliedFilters.value.splice(existingIndex, 1)
	} else {
		// Add the filter
		appliedFilters.value.push({
			field: 'status',
			value: status.toLowerCase()
		})
	}
}

// --- UTILITY FUNCTIONS ---

async function cancelRun(run: WorkflowRun) {
	try {
		await workflowRunsApi.cancel(run.id)
		await new Promise(resolve => setTimeout(resolve, 500))
		await loadData()
	} catch (err: any) {
		const errorMessage = err?.response?.data?.detail || err?.message || 'Failed to cancel workflow run'
		showSnackbar(`Failed to cancel: ${errorMessage}`, 'error')
	}
}

async function retryRun(run: WorkflowRun) {
	try {
		const newRun = await workflowRunsApi.retry(run.id)
		await new Promise(resolve => setTimeout(resolve, 500))
		await loadData()
	} catch (err: any) {
		const errorMessage = err?.response?.data?.detail || err?.message || 'Failed to retry workflow run'
		showSnackbar(`Failed to retry: ${errorMessage}`, 'error')
	}
}
</script>

<style scoped>
.stats-chip {
	cursor: pointer;
	transition: all 0.2s ease;
}

.stats-chip:hover {
	transform: scale(1.05);
	box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
}

.help-table code {
	background-color: rgba(var(--v-theme-surface-variant), 0.5);
	border-radius: 4px;
	padding: 2px 6px;
	font-family: 'Courier New', Courier, monospace;
	font-size: 0.875em;
}

.stats-card {
	/* make the outlined card border LESS visible - more subtle than search bar */
	border-color: rgba(var(--v-theme-on-surface), 0.08) !important;
	background-color: rgb(var(--v-theme-surface));
}

:deep(.workflow-runs-table) {
	background-color: transparent;
}

:deep(.workflow-runs-table .v-data-table__wrapper) {
	border-radius: 0;
}

:deep(.workflow-runs-table thead) {
	background-color: rgb(var(--v-theme-surface));
}

:deep(.workflow-runs-table thead th) {
	text-align: center !important;
}

:deep(.workflow-runs-table .v-data-table-header__content) {
	display: flex !important;
	align-items: center !important;
	justify-content: center !important;
}

:deep(.workflow-runs-table .v-data-table-header__sort-icon) {
	opacity: 0.3;
}

:deep(.workflow-runs-table th:hover .v-data-table-header__sort-icon) {
	opacity: 1;
}

:deep(.workflow-runs-table .v-data-table-header__content > span) {
	flex-grow: 0 !important;
}

:deep(.workflow-runs-table tbody tr:hover) {
	background-color: rgba(var(--v-theme-primary), 0.08) !important;
}

:deep(.workflow-runs-table tbody td) {
	padding: 8px 12px !important;
	text-align: center !important;
}

.font-mono {
	font-family: 'Courier New', Courier, monospace;
}
</style>
