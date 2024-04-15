import Vue from 'vue'
import VueRouter from 'vue-router'
import store from '@/store'
import { CHECK_AUTH, GET_POLICY_DATA } from '@/store/actions.type'
import routes from './routes'
import { checkAuthR } from '@/utils/utils'

Vue.use(VueRouter)

// Guard the route from unauthorized users.
export function guardRoute(to: any, from: any, next: any) {
  //// Check if the user is authenticated and authorized
  if (!store.getters.isAuthenticated) {
    next({ name: 'home' })
  } else {
    authorizeRoute(to, from, next)
  }
}

function authorizeRoute(to: any, from: any, next: any) {
  //// Check if the route is allowed for the current user
  if (checkAuthR(store.getters.policyData, to.path, store.getters.currentUser)) {
    return next()
  } else {
    return next({ name: 'home' })
  }
}

const router = new VueRouter({
  mode: 'history',
  routes: routes.map((route: any) => ({
    name: route.name,
    path: route.path,
    component: route.component,
    beforeEnter: (to, from, next) => {
      // Setup some per-page stuff.
      document.title = route.title

      // Auth navigation guard.
      if (!route.permissions.isPublic) {
        return guardRoute(to, from, next)
      } else  {
        next()
      }
    },
  })),
})

// Ensure we checked auth before each page load.
router.beforeEach((to, from, next) => {
  Promise.all([store.dispatch(CHECK_AUTH)]).then(() => {
    next()
  }).catch((err: any) => {
    // None of the option works! :/
    //next()
    //location.reload()
    //window.location.replace('https://vm-129-41.cloud.dkfz-heidelberg.de/#' + to.fullPath)
    // location.href = '/#' + to.fullPath
    // href also reloads, might be that reload is enough to refresh token then the next url will be successfully entered,
    // otherwise the user is redirected to the login page
    // location.reload() // works but the user is not redirected to the correct site
  });
})


router.beforeEach((to, from, next) => {
  //// Get user infor before changing the route
  Promise.all([store.dispatch(GET_POLICY_DATA)]).then(() => {
    next()
  }).catch((err: any) => {
  });
})

export default router
