import { createRouter, createWebHistory } from 'vue-router'
import { getProjectBase } from '@kaapana/base-ui'
import WorkflowRuns from '../views/WorkflowRuns.vue'
import WorkflowRunLogs from '../views/WorkflowRunLogs.vue'
import Workflows from '../views/Workflows.vue'

const routes = [
  { path: '/', redirect: '/workflows' },
  {
    path: '/workflows',
    name: 'Workflows',
    component: Workflows,
    meta: { title: 'Workflows' },
  },
  {
    path: '/runs',
    name: 'WorkflowRuns',
    component: WorkflowRuns,
    meta: { title: 'Workflow Runs' },
  },
  {
    path: '/runs/:runId(\\d+)/logs',
    name: 'WorkflowRunLogs',
    component: WorkflowRunLogs,
    props: (route: { params: { runId: string } }) => ({ runId: Number(route.params.runId) }),
    meta: { title: 'Workflow Run Details' },
  },
]

// BASE_URL is the build-time "/workflow-ui/"; the shell serves the bundle at
// /project/<short_id>/workflow-ui/, so the history base must pick the prefix
// up from the document URL. Without it no route matches and nothing renders.
const router = createRouter({
  history: createWebHistory(getProjectBase() + import.meta.env.BASE_URL),
  routes,
})

router.afterEach((to) => {
  document.title = (to.meta.title as string) || 'Workflows'
})

export default router
