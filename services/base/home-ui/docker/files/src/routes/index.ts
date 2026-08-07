import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { getProjectBase, useAuthStore } from '@kaapana/base-ui'
import { useCommonDataStore } from '@/stores/commonData'

const routes: RouteRecordRaw[] = [
  {
    name: 'home',
    path: '/',
    component: () => import('@/views/Home.vue'),
    beforeEnter: (_to, _from, next) => {
      document.title = 'Home'
      next()
    },
  },
]

const router = createRouter({
  // The document may carry the /project/<short_id> prefix (see
  // @kaapana/base-ui); the history base must include it so in-app
  // navigation stays under the project scope.
  history: createWebHistory(`${getProjectBase()}/home-ui/`),
  routes,
})

router.beforeEach((_to, _from, next) => {
  const auth = useAuthStore()
  // Proceed even on auth failure so the view mounts and renders the
  // logged-out card, instead of hanging on a swallowed rejection.
  Promise.all([auth.checkAuth()])
    .then(() => {
      next()
    })
    .catch(() => {
      next()
    })
})

router.beforeEach((_to, _from, next) => {
  const commonData = useCommonDataStore()
  Promise.all([commonData.getPolicyData()])
    .then(() => {
      next()
    })
    .catch(() => {
      next()
    })
})

export default router
