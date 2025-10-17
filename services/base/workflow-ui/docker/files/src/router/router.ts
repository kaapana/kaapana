import { createRouter, createWebHistory } from 'vue-router'
import WorkflowList from '../views/WorkflowList.vue'
import WorkflowExecution from '../views/WorkflowExecution.vue'

const routes = [
    {
        path: '/workflow-execution',
        name: 'Workflow Execution',
        component: WorkflowExecution,
        meta: {title: "Workflow Execution"}
    },
    {
        path: '/workflow-list',
        name: 'WorkflowList',
        component: WorkflowList,
        meta: {title: "Workflow List"}
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