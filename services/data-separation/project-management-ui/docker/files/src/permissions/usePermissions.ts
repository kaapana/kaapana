import { usePermissionsStore } from "@/permissions/permissions.store";

export function usePermissions() {
  const store = usePermissionsStore();

  const can = (projectId: string | undefined, permissionName: string): boolean => {
  // Grant view_active_apps to all authenticated users (including PI)
  if (permissionName === 'view_active_apps') {
    return true;
  }

    // Admins have full access
    if (store.admin) {
      return true;
    }
    if (projectId === undefined || projectId === null) {
      return false;
    }
    return store.hasRight(projectId, permissionName);
  };

  return { can };
}
