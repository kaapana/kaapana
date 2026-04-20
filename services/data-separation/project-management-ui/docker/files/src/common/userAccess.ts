import store from '@/common/store'
import { UserItem } from '@/common/types'

export function isAdminUser(user: UserItem): boolean {
  return Boolean(
    user.realm_roles &&
    (user.realm_roles.includes('project-manager') || user.realm_roles.includes('admin'))
  )
}

export function waitForStoreUser(callback: (user: UserItem) => void) {
  const interval = setInterval(() => {
    const user = store.state.user
    if (user) {
      callback(user)
      clearInterval(interval)
    }
  }, 100)
}
