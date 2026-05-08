import { createRouter, createWebHistory } from 'vue-router'
import WorkflowRuns from '../views/WorkflowRuns.vue'
import Workflows from '../views/Workflows.vue'

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
    {
        path: '/logs',
        name: 'Logs',
        component: () => import('@/views/logging/LogsOverview.vue'),
        meta: { title: 'Logs' }
    },
    {
        path: '/logs/workflow',
        name: 'WorkflowLogs',
        component: () => import('@/views/logging/WorkflowLogsPage.vue'),
        meta: { title: 'Workflow Logs' }
    },
    {
        path: '/logs/loki',
        name: 'LokiLogs',
        component: () => import('@/views/logging/LokiLogsPage.vue'),
        meta: { title: 'Loki Logs' }
    },
    {
        path: '/logs/workflow-loki',
        name: 'WorkflowLokiLogs',
        component: () => import('@/views/logging/WorkflowLokiPage.vue'),
        meta: { title: 'Workflow Loki Logs' }
    },
]

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes
})

router.afterEach((to) => {
    document.title = to.meta.title as string || 'Default Title'
})

export default router
