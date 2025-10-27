import { createRouter, createWebHistory } from 'vue-router'
import WorkflowRuns from '../views/WorkflowRuns.vue'
import Workflows from '../views/Workflows.vue'

const routes = [
    {
        path: '/workflows',
        name: 'Workflows',
        component: Workflows,
        meta: {title: "Workflows"}
    },
    {
        path: '/workflows/runs',
        name: 'WorkflowRuns',
        component: WorkflowRuns,
        meta: {title: "Workflow Runs"}
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

router.afterEach((to) => {
  document.title = to.meta.title as string || 'Default Title'
})

export default router