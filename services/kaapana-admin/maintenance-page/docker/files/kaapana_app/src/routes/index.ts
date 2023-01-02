import Vue from 'vue'
import Router from 'vue-router'
import store from '@/store'
import { CHECK_AUTH } from '@/store/actions.type'
import routes from './routes'

Vue.use(Router)

// Guard the route from unauthorized users.
function guardRoute(to: any, from: any, next: any) {
  if (!store.getters.isAuthenticated) {
    next({ name: 'home' })
  } else {
    next()
  }
}

const router = new Router({
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

export default router
