import { createRouter, createWebHistory } from 'vue-router'
import WorkflowRuns from '../views/WorkflowRuns.vue'
import Workflows from '../views/Workflows.vue'
import { getProjectBase } from '../utils/projectScope'

const routes = [
    {
        path: '/workflows',
        name: 'Workflows',
        component: Workflows,
        meta: { title: 'Workflows' }
    },
    {
        path: '/runs',
        name: 'WorkflowRuns',
        component: WorkflowRuns,
        meta: { title: 'Workflow Runs' }
    },
]

// BASE_URL is the build-time "/workflow-ui"; the shell serves the bundle at
// /project/<short_id>/workflow-ui/, so the history base must pick the prefix
// up from the document URL — without it no route matches and nothing renders.
const router = createRouter({
    history: createWebHistory(getProjectBase() + import.meta.env.BASE_URL),
    routes
})

router.afterEach((to) => {
    document.title = to.meta.title as string || 'Default Title'
})

export default router
