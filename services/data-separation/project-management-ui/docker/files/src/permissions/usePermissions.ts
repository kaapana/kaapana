import { usePermissionsStore } from "@/permissions/permissions.store";
import { isAdminUser } from "@/common/userAccess";
import vuexStore from "@/common/store";

export function usePermissions() {
  const permissionsStore = usePermissionsStore();

  /**
   * Check whether the current user can perform an action on a project resource.
   *
   * Order of evaluation:
   *   1. Admin → always true
   *   2. AII rights (from DB, loaded at app startup)
   *   3. For whitelist-sensitive permissions (launch_application, delete_active_apps),
   *      also check whether the specific resource is allowed by the project whitelist.
   */
  const can = (
    projectId: string | undefined,
    permissionName: string,
    resourceName?: string,
  ): boolean => {
    // 1. Admins bypass everything
    if (vuexStore.state.user && isAdminUser(vuexStore.state.user)) {
      return true;
    }

    if (!projectId) return false;

    // 2. Check AII rights
    if (!permissionsStore.hasRight(projectId, permissionName)) return false;

    // 3. For whitelist-sensitive actions, also check the project whitelist
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
