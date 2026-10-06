import { createRouter, createWebHistory } from 'vue-router'
import Index from '@/pages/index.vue'
import Project from '@/pages/project.vue'
import RoleRights from '@/pages/role-rights.vue'
import store from '@/common/store'
import { isAdminUser } from '@/common/userAccess'

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
    beforeEnter: async () => (isAdminUser(await store.userLoaded) ? true : '/'),
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

export default router
