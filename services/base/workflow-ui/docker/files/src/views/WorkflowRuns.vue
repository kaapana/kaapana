<template>
	<v-container fluid>
		<v-container style="max-width: 1800px;">
			<v-row>
				<v-col cols="12" class="d-flex justify-space-between align-center mb-4">
					<div>
						<h2 class="mb-0">Workflow Runs</h2>
						<div class="text--secondary">Grouped by workflow title → version; expand to see runs and actions</div>
					</div>

					<div class="d-flex align-center">
						<v-btn outlined small color="primary" @click="loadRuns">Refresh</v-btn>
						<v-menu offset-y>
							<template #activator="{ on, attrs }">
								<v-btn outlined small v-bind="attrs" v-on="on">Filters</v-btn>
							</template>
							<v-list>
								<v-list-item @click="clearFilters">Clear filters</v-list-item>
								<!-- Additional global filter items can be added here -->
							</v-list>
						</v-menu>
					</div>
				</v-col>
			</v-row>

						<v-row>
							<v-col cols="12">
								<v-progress-linear v-if="loading" indeterminate color="primary" />

								<v-alert v-else-if="error" type="error" prominent>{{ error }}</v-alert>

								<v-card class="theme--dark pa-4">
									<div class="d-flex justify-space-between align-center mb-3">
										<div>
											<strong>Grouped Workflows</strong>
											<div class="text--secondary">Expand a title to see versions and runs</div>
										</div>
										<div>
											<v-text-field hide-details dense placeholder="Search for Workflow, version, run id or external id" v-model="search" append-icon="mdi-magnify" style="max-width:640px" clearable />
										</div>
									</div>

									<grouped-workflow-runs :titleGroups="filteredTitleGroups" :lifecycleStatuses="lifecycleStatuses"
										@view="viewRun" @cancel="cancelRun" @retry="retryRun" @refresh="loadRuns" />
								</v-card>
							</v-col>
						</v-row>
		</v-container>
	</v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import GroupedWorkflowRuns from '@/components/GroupedWorkflowRuns.vue'
import { workflowRunsApi } from '@/api/workflowRuns'
import type { WorkflowRun } from '@/types/workflowRun'
import { WorkflowRunStatus } from '@/types/enum'

const loading = ref(true)
const error = ref<string | null>(null)
const runs = ref<WorkflowRun[]>([])
const search = ref('')

async function loadRuns() {
	loading.value = true
	error.value = null
	try {
		const data = await workflowRunsApi.getAll()
		runs.value = Array.isArray(data) ? data : []
	} catch (err) {
		console.error(err)
		error.value = 'Failed to fetch workflow runs.'
		runs.value = []
	} finally {
		loading.value = false
	}
}

function clearFilters() {
	// for now simply reload everything
	loadRuns()
}

onMounted(loadRuns)

const titleGroups = computed(() => {
	const tmap = new Map<string, { title: string; versionGroups: any[]; statusCounts: Record<string, number> }>()

		runs.value.forEach((r: WorkflowRun) => {
		const title = r.workflow?.title || 'Unknown'
		const version = r.workflow?.version ?? 0

		if (!tmap.has(title)) {
			tmap.set(title, { title, versionGroups: [], statusCounts: {} })
		}

		const tg = tmap.get(title)!
		let vg = tg.versionGroups.find((x: any) => x.version === version)
		if (!vg) {
			vg = { version, runs: [], statusCounts: {}, versionOptions: [] }
			tg.versionGroups.push(vg)
		}

		vg.runs.push(r)
		vg.statusCounts[r.lifecycle_status] = (vg.statusCounts[r.lifecycle_status] || 0) + 1
		tg.statusCounts[r.lifecycle_status] = (tg.statusCounts[r.lifecycle_status] || 0) + 1
	})

	// finalize groups: sort runs and populate version options
	const result: any[] = []
	tmap.forEach(tg => {
		tg.versionGroups.sort((a: any, b: any) => b.version - a.version)
		tg.versionGroups.forEach((vg: any) => {
			vg.runs.sort((a: WorkflowRun, b: WorkflowRun) => +new Date(b.created_at) - +new Date(a.created_at))
			vg.versionOptions = tg.versionGroups.map((x: any) => x.version)
		})
		result.push(tg)
	})

	return result
})

const filteredTitleGroups = computed(() => {
	const q = (search.value || '').toLowerCase().trim()
	if (!q) return titleGroups.value

	// filter title groups by title, version, run id, or external id
	return titleGroups.value
		.map((tg: any) => {
			const matchedVersionGroups = tg.versionGroups
				.map((vg: any) => {
					const matchedRuns = vg.runs.filter((r: WorkflowRun) => {
						if (!r) return false
						const titleMatch = (tg.title || '').toLowerCase().includes(q)
						const versionMatch = String(vg.version).toLowerCase().includes(q)
						const runIdMatch = String(r.id).toLowerCase().includes(q)
						const externalIdMatch = (r.external_id || '').toLowerCase().includes(q)
						return titleMatch || versionMatch || runIdMatch || externalIdMatch
					})
					if (matchedRuns.length === 0) return null
					return { ...vg, runs: matchedRuns }
				})
				.filter((x: any) => x)

			if (matchedVersionGroups.length === 0) return null
			return { ...tg, versionGroups: matchedVersionGroups }
		})
		.filter((x: any) => x)
})

// ordered list of lifecycle statuses to display in headers
const lifecycleStatuses: WorkflowRunStatus[] = [
	WorkflowRunStatus.RUNNING,
	WorkflowRunStatus.SCHEDULED,
	WorkflowRunStatus.PENDING,
	WorkflowRunStatus.COMPLETED,
	WorkflowRunStatus.ERROR,
	WorkflowRunStatus.CANCELED,
]

// register components (script setup auto-registers imported components)
const components = { GroupedWorkflowRuns }

function formatDate(d: string) {
	try {
		return new Date(d).toLocaleString()
	} catch {
		return d
	}
}

function statusColor(status: string) {
	switch (status) {
		case 'Running':
		case 'Scheduled':
			return 'blue'
		case 'Pending':
			return 'grey'
		case 'Completed':
			return 'green'
		case 'Error':
			return 'red'
		case 'Canceled':
			return 'orange'
		default:
			return 'grey'
	}
}

function canCancel(run: WorkflowRun) {
	return ['Pending', 'Scheduled', 'Running'].includes(run.lifecycle_status)
}

function canRetry(run: WorkflowRun) {
	return ['Error', 'Canceled', 'Completed'].includes(run.lifecycle_status)
}

async function cancelRun(run: WorkflowRun) {
	try {
		await workflowRunsApi.cancel(run.id)
		await loadRuns()
	} catch (err) {
		console.error(err)
	}
}

async function retryRun(run: WorkflowRun) {
	try {
		await workflowRunsApi.retry(run.id)
		await loadRuns()
	} catch (err) {
		console.error(err)
	}
}

function viewRun(run: WorkflowRun) {
	console.log('View run', run.id)
}

async function refreshWorkflow(workflowRef: { title: string; version: number }) {
	loading.value = true
	error.value = null
	try {
		const data = await workflowRunsApi.getAll({ workflow_title: workflowRef.title, workflow_version: workflowRef.version })
		runs.value = Array.isArray(data) ? data : []
	} catch (err) {
		console.error(err)
		error.value = 'Failed to refresh'
		runs.value = []
	} finally {
		loading.value = false
	}
}

function filterByWorkflow(workflowRef: { title: string; version: number }) {
	refreshWorkflow(workflowRef)
}

function onSelectVersion(title: string, val: number | string) {
	// cast number if needed
	const version = typeof val === 'string' ? Number(val) : val
	filterByWorkflow({ title, version: Number(version) })
}

function makeOnSelectVersion(title: string) {
	return (val: number | string) => onSelectVersion(title, val)
}
</script>
