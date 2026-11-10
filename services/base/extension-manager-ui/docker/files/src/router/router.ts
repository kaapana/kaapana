import { createRouter, createWebHistory } from 'vue-router'
import CatalogView from '@/views/CatalogView.vue'
import ExtensionsView from '@/views/ExtensionsView.vue'
import RepositoriesView from '@/views/RepositoriesView.vue'

const routes = [
  { path: '/', redirect: '/catalog' },
  { path: '/catalog', name: 'Catalog', component: CatalogView, meta: { title: 'Catalog' } },
  {
    path: '/extensions',
    name: 'Extensions',
    component: ExtensionsView,
    meta: { title: 'Extensions' },
  },
  {
    path: '/repositories',
    name: 'Repositories',
    component: RepositoriesView,
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
