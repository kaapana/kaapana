import { createRouter, createWebHistory, type RouteParams, type Router } from "vue-router";
import HomeView from "@/views/HomeView.vue";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "Home",
      component: HomeView,
    },
    {
      path: "/wazuh",
      name: "wazuh",
      // route level code-splitting
      // this generates a separate chunk (About.[hash].js) for this route
      // which is lazy-loaded when the route is visited.
      component: () => import("@/views/WazuhView.vue"),
      children: [
        {
          path: "",
          name: "agentlist",
          component: () => import("@/views/wazuh/AgentListView.vue")
        },
        {
          path: "agents/:agent_id/policies",
          name: "policylist",
          component: () => import("@/views/wazuh/PolicyListView.vue")
        },
        {
          path: "agents/:agent_id/policies/:policy_id",
          name: "policy",
          component: () => import("@/views/wazuh/PolicyView.vue")
        },
        {
          path: "agents/:agent_id/vulnerabilities",
          name: "vulnerabilitylist",
          component: () => import("@/views/wazuh/VulnerabilityListView.vue")
        },
        {
          path: "agents/:agent_id/fileintegritymonitoring",
          name: "fileintegritylist",
          component: () => import("@/views/wazuh/FileIntegrityListView.vue")
        }
      ]
    },
    {
      path: "/stackrox",
      name: "StackRox",
      // route level code-splitting
      // this generates a separate chunk (About.[hash].js) for this route
      // which is lazy-loaded when the route is visited.
      component: () => import("@/views/StackRoxView.vue"),
      children: [
        {
          path: "",
          name: "overview",
          component: () => import("@/views/stackrox/OverviewView.vue")
        },
        {
          path: "networkgraph",
          name: "networkgraph",
          component: () => import("@/views/stackrox/NetworkGraphView.vue")
        },
        {
          path: "policyviolations",
          name: "policyviolations",
          component: () => import("@/views/stackrox/PolicyViolationView.vue")
        },
        {
          path: "images",
          name: "images",
          component: () => import("@/views/stackrox/Images.vue")
        },
        {
          path: "deployments",
          name: "deployments",
          component: () => import("@/views/stackrox/DeploymentsView.vue")
        },
        {
          path: "secrets",
          name: "secrets",
          component: () => import("@/views/stackrox/SecretsView.vue")
        }
      ]
    },
    { path: '/:pathMatch(.*)*', name: "notfound", redirect: '/' },
  ],
});

export function navigateTo(name: string, params: RouteParams) {
  router.push({name: name, params: params});
}

export default router;
