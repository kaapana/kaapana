import { createRouter, createWebHistory } from 'vue-router'
import { getProjectBase, useAuthStore } from '@kaapana/base-ui'

const router = createRouter({
  // The document may carry the /project/<short_id> prefix (see
  // @kaapana/base-ui); the history base must include it so in-app
  // navigation stays under the project scope.
  history: createWebHistory(`${getProjectBase()}/federated-ui/`),
  routes: [
    {
      name: 'runner-instances',
      path: '/',
      component: () => import('@/views/RunnerInstances.vue'),
      beforeEnter: (to, from, next) => {
        document.title = 'Instance Overview'
        next()
      },
    },
  ],
})

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  // Proceed even when the auth check fails: the traefik forwardAuth gateway is
  // the real auth boundary in front of this iframe, so mount the view instead
  // of hanging on a swallowed rejection.
  auth
    .checkAuth()
    .then(() => {
      next()
    })
    .catch(() => {
      next()
    })
})

export default router
