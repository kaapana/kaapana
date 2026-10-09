import { createRouter, createWebHistory } from 'vue-router'
import { getProjectBase, useAuthStore } from '@kaapana/base-ui'

const router = createRouter({
  history: createWebHistory(`${getProjectBase()}/federated-ui/`),
  routes: [
    {
      name: 'runner-instances',
      path: '/',
      component: () => import('@/views/RunnerInstances.vue'),
      beforeEnter: (to, from, next) => {
        document.title = 'Instance overview'
        next()
      },
    },
  ],
})

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
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
