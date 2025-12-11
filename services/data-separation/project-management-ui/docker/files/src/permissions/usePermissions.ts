import { usePermissionsStore } from "@/permissions/permissions.store";

export function usePermissions() {
  const store = usePermissionsStore();

  const can = (projectId: string | undefined, permissionName: string): boolean => {
    if (projectId === undefined || projectId === null) {
      return false;
    }

    return store.hasRight(projectId, permissionName);
  };

  return { can };
}
