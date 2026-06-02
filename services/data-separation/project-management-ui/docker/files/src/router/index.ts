/**
 * router/index.ts
 *
 * Manual route configuration for project management UI
 */

// Composables
import { createRouter, createWebHistory } from 'vue-router'
import Index from '@/pages/index.vue'
import Project from '@/pages/project.vue'
import RoleRights from '@/pages/role-rights.vue'

// Define routes manually to avoid auto-route conflicts
const routes = [
  {
    path: '/',
    name: 'Index',
    component: Index,
  },
  {
    path: '/project/:id',
    component: Project,
    name: 'ProjectDetail'
  },
  {
    path: '/project/:id/:name',
    component: Project,
    name: 'ProjectDetailWithName'
  },
  {
    path: '/role-rights',
    name: 'RoleRights',
    component: RoleRights,
  },
  // Catch-all redirect to home
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory('/projects-ui'),
  routes,
})

// Workaround for https://github.com/vitejs/vite/issues/11804
router.onError((err, to) => {
  if (err?.message?.includes?.('Failed to fetch dynamically imported module')) {
    if (!localStorage.getItem('vuetify:dynamic-reload')) {
      console.log('Reloading page to fix dynamic import error')
      localStorage.setItem('vuetify:dynamic-reload', 'true')
      location.assign(to.fullPath)
    } else {
      console.error('Dynamic import error, reloading page did not fix it', err)
    }
  } else {
    console.error(err)
  }
})

router.isReady().then(() => {
  localStorage.removeItem('vuetify:dynamic-reload')
})

export default router
