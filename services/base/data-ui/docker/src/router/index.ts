import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import EntitiesPage from '@/views/EntitiesPage.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'entities',
    component: EntitiesPage,
  },
]

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router
