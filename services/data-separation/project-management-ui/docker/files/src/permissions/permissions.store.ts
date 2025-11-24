import { defineStore } from "pinia";
import { aiiApiGet } from "@/common/aiiApi.service";

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
    initialized: false
  }),

  actions: {
    async loadUserRights(userId?: string): Promise<void> {
      if (!userId) {
        console.warn("loadUserRights called without userId");
        return;
      }

      this.rights = await aiiApiGet('/aii/users/' + userId + '/rights');

      // Normalize rights into a project → rights map
      this.rightsByProject = this.rights.reduce<RightsByProject>((acc, r) => {
        if (!acc[r.project_id]) acc[r.project_id] = [];
        acc[r.project_id].push({
          name: r.name,
          description: r.description
        });
        return acc;
      }, {});

      this.initialized = true;
    },

    hasRight(projectId: string, name: string): boolean {
      const rights = this.rightsByProject[projectId];
      if (!rights) return false;
      return rights.some(r => r.name === name);
    }
  }
});
