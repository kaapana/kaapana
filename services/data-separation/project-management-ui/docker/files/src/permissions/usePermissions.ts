import { checkRoleAuthR } from '@kaapana/base-ui'
import { usePermissionsStore } from '@/permissions/permissions.store'
import { usePolicyStore } from '@/stores/policy'
import userStore from '@/common/store'

// The request each project permission stands for, as the gateway sees it (the
// /project/<id> prefix is stripped before the policy is evaluated).
const PERMISSION_REQUESTS: Record<string, { path: (projectId: string) => string; method: string }> =
  {
    manage_users: { path: (id) => `/aii/projects/${id}/role/`, method: 'POST' },
    manage_workflow_whitelist: {
      path: (id) => `/aii/projects/${id}/software-mappings`,
      method: 'POST',
    },
    manage_applications_whitelist: {
      path: (id) => `/aii/projects/${id}/multiinstallable-whitelist`,
      method: 'PUT',
    },
    view_applications: { path: () => '/kube-helm-api/extensions', method: 'GET' },
    view_active_apps: { path: () => '/kube-helm-api/active-applications', method: 'GET' },
    launch_application: { path: () => '/kube-helm-api/helm-install-chart', method: 'POST' },
    delete_active_apps: { path: () => '/kube-helm-api/helm-delete-chart', method: 'POST' },
  }

export function usePermissions() {
  const permissionsStore = usePermissionsStore()
  const policyStore = usePolicyStore()

  /**
   * Whether the gateway will let the current user perform an action on a
   * project, so the view can hide or disable what would be refused. Display
   * only: the gateway enforces the policy.
   *
   *   1. A role grant in the OPA policy data allows the request outright.
   *   2. Otherwise the user's AII right for the project does; the gateway
   *      turns it into a claim rule, which the policy data cannot show.
   *   3. Launching and deleting an application additionally needs the
   *      application on the project whitelist, as kube-helm checks it for
   *      everyone but admins.
   */
  const can = (
    projectId: string | undefined,
    permissionName: string,
    resourceName?: string,
  ): boolean => {
    if (!projectId) return false

    const request = PERMISSION_REQUESTS[permissionName]
    const roles = userStore.state.user?.realm_roles ?? []
    if (
      request &&
      roles.some((role) =>
        checkRoleAuthR(policyStore.policyData, request.path(projectId), role, request.method),
      )
    ) {
      return true
    }

    if (!permissionsStore.hasRight(projectId, permissionName)) return false

    if (
      resourceName &&
      (permissionName === 'launch_application' || permissionName === 'delete_active_apps')
    ) {
      return permissionsStore.isResourceAllowed(projectId, resourceName);
    }

    return true;
  };

  return { can };
}
