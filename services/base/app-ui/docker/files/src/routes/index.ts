import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { getProjectBase, useAuthStore } from '@kaapana/base-ui'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/tasks' },
  {
    name: 'tasks',
    path: '/tasks',
    component: () => import('@/views/ActiveApplications.vue'),
    meta: { title: 'Tasks', mode: 'tasks' },
  },
  {
    name: 'apps',
    path: '/apps',
    component: () => import('@/views/ActiveApplications.vue'),
    meta: { title: 'Apps', mode: 'apps' },
  },
]

const router = createRouter({
  // The document may carry the /project/<short_id> prefix (see
  // @kaapana/base-ui); the history base must include it so in-app
  // navigation stays under the project scope.
  history: createWebHistory(`${getProjectBase()}/app-ui/`),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  // Proceed even when the auth check fails: the traefik forwardAuth gateway is
  // the real auth boundary in front of this iframe, so mount the view instead
  // of blocking the navigation.
  try {
    await auth.checkAuth()
  } catch {
    // fall through and mount anyway
  }
  if (to.meta.title) {
    document.title = to.meta.title as string
  }
  return true
})

export default router
