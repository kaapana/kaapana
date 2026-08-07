import { defineStore } from 'pinia'
import { fetchUserinfo, logout as authLogout, type UserinfoJwt } from '@/api/auth'
import { useViewStateStore } from '@/stores/viewState'

export interface User {
  username: string
  roles: string[]
  groups: string[]
  id: string
}

function jwtToUser(jwt: UserinfoJwt): User {
  const startWithBackSlashRgx = /^\//i
  return {
    username: jwt.preferredUsername,
    roles: jwt.groups
      .filter((group) => group.startsWith('role:'))
      .map((role) => role.slice('role:'.length)),
    groups: jwt.groups
      .filter((group) => !group.startsWith('role:'))
      .map((groupname) => groupname.replace(startWithBackSlashRgx, '')),
    id: jwt.user,
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    isAuthenticated: false,
    user: null as User | null,
  }),
  actions: {
    async ensureLoaded() {
      if (this.isAuthenticated) return
      const jwt = await fetchUserinfo()
      this.user = jwtToUser(jwt)
      this.isAuthenticated = true
    },
    /** Manual logout: gated by the view-dirty confirm. The idle timer calls logout() directly. */
    async requestLogout() {
      if (!(await useViewStateStore().confirmLeave())) return
      this.logout()
    },
    logout() {
      this.isAuthenticated = false
      this.user = null
      authLogout()
    },
  },
})
