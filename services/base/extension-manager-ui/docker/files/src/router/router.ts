import { createRouter, createWebHistory } from 'vue-router'
import Extensions from '@/views/Extensions.vue'

const routes = [
  {
    path: '/',
    redirect: '/extensions',
  },
  {
    path: '/extensions',
    name: 'Extensions',
    component: Extensions,
    meta: { title: 'Extension Manager' },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.afterEach((to) => {
  document.title = (to.meta.title as string) || 'Extension Manager'
})

export default router
