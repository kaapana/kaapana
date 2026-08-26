import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { getProjectBase, useAuthStore } from '@kaapana/base-ui'

const routes: RouteRecordRaw[] = [
  {
    name: 'workflows',
    path: '/',
    component: () => import('@/views/Workflows.vue'),
    meta: { title: 'Workflow List' },
  },
]

const router = createRouter({
  // The document may carry the /project/<short_id> prefix (see
  // @kaapana/base-ui); the history base must include it so in-app
  // navigation stays under the project scope.
  history: createWebHistory(`${getProjectBase()}/workflow-list-ui/`),
  routes,
})

router.beforeEach((to) => {
  document.title = String(to.meta.title ?? 'Kaapana')
})

router.beforeEach(async () => {
  const auth = useAuthStore()
  // Proceed even when the auth check fails: the traefik forwardAuth gateway is
  // the real auth boundary in front of this iframe, so mount the view instead
  // of blocking the navigation.
  try {
    await auth.checkAuth()
  } catch {
    // mount anyway
  }
  return true
})

export default router
