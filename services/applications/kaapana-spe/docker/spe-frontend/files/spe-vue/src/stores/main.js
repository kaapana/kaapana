import { defineStore } from 'pinia';

export const useMainStore = defineStore('main', {
  state: () => ({
    users: [],
    scripts: [],
    data: [],
  }),
  actions: {
    applyForAccess(user) {
      this.users.push({ ...user, status: 'pending' });
    },
    approveUser(userId) {
      const user = this.users.find((u) => u.id === userId);
      if (user) user.status = 'approved';
    },
    grantAccess(userId, scriptId) {
      const user = this.users.find((u) => u.id === userId);
      if (user) {
        if (!user.access) user.access = [];
        user.access.push(scriptId);
      }
    },
  },
});