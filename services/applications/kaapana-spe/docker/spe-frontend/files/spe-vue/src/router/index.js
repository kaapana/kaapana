import { createRouter, createWebHistory } from "vue-router";
import UserApplication from "../views/UserApplication.vue";
import ScriptExecution from "../views/ScriptExecution.vue";
import AdminManagement from "../views/AdminManagement.vue";

const routes = [
  { path: "/", component: UserApplication },
  { path: "/execute", component: ScriptExecution },
  { path: "/admin", component: AdminManagement },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
