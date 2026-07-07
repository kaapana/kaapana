import { defineStore } from "pinia";
import { aiiApiGet } from "@/common/services";

export interface UserRight {
  name: string;
  description: string;
  claim_key: string;
  claim_value: string;
  project_id: string;
}

export interface NormalizedRights {
  name: string;
  description: string;
}

export interface RightsByProject {
  [projectId: string]: NormalizedRights[];
}

export const usePermissionsStore = defineStore("permissions", {
  state: () => ({
    rights: [] as UserRight[],
    rightsByProject: {} as RightsByProject,
    whitelistByProject: {} as Record<string, string[]>,
    initialized: false,
  }),

  actions: {
    async loadUserRights(userId?: string): Promise<void> {
      if (!userId) {
        console.warn("loadUserRights called without userId");
        return;
      }

      this.rights = await aiiApiGet('/aii/users/' + userId + '/rights');

      this.rightsByProject = this.rights.reduce<RightsByProject>((acc, r) => {
        if (!acc[r.project_id]) acc[r.project_id] = [];
        acc[r.project_id].push({ name: r.name, description: r.description });
        return acc;
      }, {});

      this.initialized = true;
    },

    async loadProjectWhitelist(projectId: string): Promise<void> {
      if (!projectId) return;
      try {
        const whitelist = await aiiApiGet(`projects/${projectId}/multiinstallable-whitelist`);
        this.whitelistByProject[projectId] = Array.isArray(whitelist) ? whitelist : [];
      } catch (error) {
        console.error('Failed to load project whitelist:', error);
      }
    },

    hasRight(projectId: string, name: string): boolean {
      const rights = this.rightsByProject[projectId];
      if (!rights) return false;
      return rights.some(r => r.name === name);
    },

    // Handles both exact names (launch) and suffixed release names (delete)
    isResourceAllowed(projectId: string, resourceName: string): boolean {
      const whitelist = this.whitelistByProject[projectId];
      if (whitelist === undefined) return false; // not loaded yet — fail closed
      if (whitelist.length === 0) return true;  // empty = all allowed
      return whitelist.some(
        entry => resourceName === entry || resourceName.startsWith(entry + '-')
      );
    },
  }
});
