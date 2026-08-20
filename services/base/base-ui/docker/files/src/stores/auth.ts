import { defineStore } from 'pinia'
import AuthService, { type UserinfoJwt } from '../utils/authService'

export interface User {
  username: string
  roles: string[]
  groups: string[]
  id: string
}

const startWithBackSlashRgx = /^\//i

export const useAuthStore = defineStore('auth', {
  state: () => ({
    isAuthenticated: false,
    user: {} as User,
    errors: {} as unknown,
  }),
  getters: {
    currentUser: (state): User => state.user,
  },
  actions: {
    async checkAuth(): Promise<void> {
      try {
        const jwt: UserinfoJwt = await AuthService.getToken()
        this.isAuthenticated = true
        this.user = {
          username: jwt.preferredUsername,
          roles: jwt.groups
            .filter((group) => group.startsWith('role:'))
            .map((role) => role.slice('role:'.length)),
          groups: jwt.groups
            .filter((group) => !group.startsWith('role:'))
            .map((groupname) => groupname.replace(startWithBackSlashRgx, '')),
          id: jwt.user,
        }
        this.errors = {}
      } catch (err) {
        console.log('CHECK_AUTH Error')
        console.log(err)
        this.errors = err
        this.isAuthenticated = false
        this.user = {} as User
        throw err
      }
    },
    logout() {
      this.isAuthenticated = false
      this.user = {} as User
      this.errors = {}
      AuthService.logout()
    },
  },
})
