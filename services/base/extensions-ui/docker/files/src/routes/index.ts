import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { getProjectBase, useAuthStore } from '@kaapana/base-ui'
import { useCommonDataStore } from '@/stores/commonData'

const routes: RouteRecordRaw[] = [
  {
    name: 'extensions',
    path: '/',
    component: () => import('@/views/Extensions.vue'),
    meta: { title: 'Extensions' },
  },
]

const router = createRouter({
  // The document may carry the /project/<short_id> prefix (see
  // @kaapana/base-ui); the history base must include it so in-app
  // navigation stays under the project scope.
  history: createWebHistory(`${getProjectBase()}/extensions-ui/`),
  routes,
})

// Auth failures are swallowed so the view still renders: the gateway enforces
// auth in front of this iframe.
router.beforeEach(async (to) => {
  if (to.meta.title) document.title = String(to.meta.title)
  const auth = useAuthStore()
  try {
    await auth.checkAuth()
  } catch (err) {
    // ignore
  }
  // The policy decides which admin-only controls the view renders, so load it
  // before the view mounts or they flash in and out. The store swallows its own
  // failures, and an unloaded policy hides them (fail closed).
  await useCommonDataStore().getPolicyData()
  return true
})

export default router
