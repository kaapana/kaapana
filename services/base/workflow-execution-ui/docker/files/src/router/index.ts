import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { getProjectBase, useAuthStore } from '@kaapana/base-ui'

const routes: RouteRecordRaw[] = [
  {
    name: 'workflow-execution',
    path: '/',
    component: () => import('@/views/WorkflowExecution.vue'),
    beforeEnter: (to, from, next) => {
      document.title = 'Workflow Execution'
      next()
    },
  },
]

const router = createRouter({
  // The document may carry the /project/<short_id> prefix (see
  // @kaapana/base-ui); the history base must include it so in-app
  // navigation stays under the project scope.
  history: createWebHistory(`${getProjectBase()}/workflow-execution-ui/`),
  routes,
})

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  // Proceed even when the auth check fails: the traefik forwardAuth gateway is
  // the real auth boundary in front of this iframe, so mount the view instead
  // of hanging on a swallowed rejection.
  Promise.all([auth.checkAuth()])
    .then(() => {
      next()
    })
    .catch(() => {
      next()
    })
})

export default router
