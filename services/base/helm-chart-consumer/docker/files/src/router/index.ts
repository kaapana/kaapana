import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useMockStore } from '@/stores/mock'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/applications' },
  {
    path: '/applications',
    component: () => import('@/views/ApplicationsView.vue'),
    meta: { title: 'Applications' },
  },
  {
    path: '/applications/:name',
    component: () => import('@/views/ApplicationDetailsView.vue'),
    props: true,
    meta: { title: 'Application' },
  },
  {
    path: '/catalog',
    component: () => import('@/views/CatalogView.vue'),
    meta: { title: 'Application Catalog' },
  },
  {
    path: '/catalog/:appId/deploy',
    component: () => import('@/views/DeployView.vue'),
    props: true,
    meta: { title: 'Deploy application' },
  },
  {
    path: '/availability',
    component: () => import('@/views/AvailabilityView.vue'),
    meta: { title: 'Application Availability' },
  },
  {
    path: '/projects',
    component: () => import('@/views/ProjectsView.vue'),
    meta: { title: 'Projects' },
  },
  {
    path: '/other/:entry',
    component: () => import('@/views/OtherView.vue'),
    props: true,
    meta: { title: 'Kaapana' },
  },
  { path: '/:pathMatch(.*)*', redirect: '/applications' },
]

const router = createRouter({
  history: createWebHistory('/'),
  routes,
})

// Stands in for the shell's unsaved-changes check: leaving a dirty view asks first.
router.beforeEach((to, from) => {
  const mock = useMockStore()
  if (mock.dirty && to.fullPath !== from.fullPath) {
    mock.pendingLeave = { kind: 'route', to: to.fullPath }
    return false
  }
  return true
})

router.afterEach((to) => {
  document.title = `${(to.meta.title as string) || 'Kaapana'} · Kaapana UI mock`
})

export default router
