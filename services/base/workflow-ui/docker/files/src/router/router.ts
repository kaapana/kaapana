import { createRouter, createWebHistory } from 'vue-router'
import WorkflowRuns from '../views/WorkflowRuns.vue'
import Workflows from '../views/Workflows.vue'

const routes = [
    {
        path: '/workflows',
        name: 'Workflows',
        component: Workflows,
        meta: { title: "Workflows" }
    },
    {
        path: '/runs',
        name: 'WorkflowRuns',
        component: WorkflowRuns,
        meta: { title: "Workflow Runs" }
    }
]

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes
})

router.afterEach((to) => {
    document.title = to.meta.title as string || 'Default Title'
})

export default router