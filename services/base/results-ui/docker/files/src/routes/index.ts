import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { getProjectBase, useAuthStore } from '@kaapana/base-ui'

const routes: RouteRecordRaw[] = [
  {
    name: 'results-browser',
    path: '/',
    component: () => import('@/views/ResultsBrowser.vue'),
    meta: { title: 'Workflow Results' },
  },
]

const router = createRouter({
  // The document may carry the /project/<short_id> prefix (see
  // @kaapana/base-ui); the history base must include it so in-app
  // navigation stays under the project scope.
  history: createWebHistory(`${getProjectBase()}/results-ui/`),
  routes,
})

router.beforeEach((to) => {
  document.title = (to.meta.title as string) || document.title
})

router.beforeEach(async () => {
  const auth = useAuthStore()
  try {
    await auth.checkAuth()
  } catch (err) {
    // Non-blocking: the traefik forwardAuth gateway is the real auth boundary.
  }
  return true
})

export default router
