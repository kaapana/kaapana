import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { getProjectBase } from '@kaapana/base-ui'
import EntitiesPage from '@/views/EntitiesPage.vue'

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'entities', component: EntitiesPage },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(getProjectBase() + import.meta.env.BASE_URL),
  routes,
})

export default router
