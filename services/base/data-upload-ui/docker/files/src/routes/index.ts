import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { getProjectBase, useAuthStore } from '@kaapana/base-ui'

const routes: RouteRecordRaw[] = [
  {
    name: 'data-upload',
    path: '/',
    component: () => import('@/views/DataUpload.vue'),
    beforeEnter: (_to, _from, next) => {
      document.title = 'Data Upload'
      next()
    },
  },
]

const router = createRouter({
  // The document may carry the /project/<short_id> prefix (see
  // @kaapana/base-ui); the history base must include it so in-app
  // navigation stays under the project scope.
  history: createWebHistory(`${getProjectBase()}/data-upload-ui/`),
  routes,
})

router.beforeEach((_to, _from, next) => {
  const auth = useAuthStore()
  // Proceed even on auth failure so the view mounts instead of hanging on a
  // swallowed rejection; the traefik forwardAuth gateway is the real auth
  // boundary in front of this iframe.
  Promise.all([auth.checkAuth()])
    .then(() => {
      next()
    })
    .catch(() => {
      next()
    })
})

export default router
