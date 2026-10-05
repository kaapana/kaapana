import { createRouter, createWebHistory } from 'vue-router'
import Catalog from '@/views/Catalog.vue'
import Extensions from '@/views/Extensions.vue'
import Repositories from '@/views/Repositories.vue'

const routes = [
  { path: '/', redirect: '/catalog' },
  { path: '/catalog', name: 'Catalog', component: Catalog, meta: { title: 'Catalog' } },
  { path: '/extensions', name: 'Extensions', component: Extensions, meta: { title: 'Extensions' } },
  {
    path: '/repositories',
    name: 'Repositories',
    component: Repositories,
    meta: { title: 'Repositories' },
  },
  { path: '/:pathMatch(.*)*', redirect: '/catalog' },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.afterEach((to) => {
  document.title = to.meta.title
    ? `${to.meta.title as string} · Extension Manager`
    : 'Extension Manager'
})

export default router
