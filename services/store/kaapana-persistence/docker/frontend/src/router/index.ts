// Composables
import { createRouter, createWebHistory } from "vue-router";

const routes = [
  {
    path: "/",
    component: () => import("@/layouts/default/Default.vue"),
    children: [
      {
        path: "",
        name: "Home",
        // route level code-splitting
        // this generates a separate chunk (about.[hash].js) for this route
        // which is lazy-loaded when the route is visited.
        component: () =>
          import(/* webpackChunkName: "home" */ "@/views/Home.vue"),
      },
    ],
  },
  {
    path: "/urn/:urn?",
    component: () => import("@/layouts/default/Default.vue"),
    children: [
      {
        path: "/urn/:urn?",
        name: "URN",
        component: () =>
          import(/* webpackChunkName: "urn" */ "@/views/URN.vue"),
        props: true,
      },
    ],
  },
  {
    path: "/schema",
    component: () => import("@/layouts/default/Default.vue"),
    children: [
      {
        path: "/schema",
        name: "Schema",
        component: () =>
          import(/* webpackChunkName: "schema" */ "@/views/Schema.vue"),
      },
    ],
  },
  {
    path: "/object",
    component: () => import("@/layouts/default/Default.vue"),
    children: [
      {
        path: "/object",
        name: "object",
        component: () =>
          import(/* webpackChunkName: "object" */ "@/views/Object.vue"),
      },
    ],
  },
  {
    path: "/cas",
    component: () => import("@/layouts/default/Default.vue"),
    children: [
      {
        path: "/cas",
        name: "CAS",
        component: () =>
          import(/* webpackChunkName: "cas" */ "@/views/CAS.vue"),
      },
    ],
  },
  {
    path: "/api",
    component: () => import("@/layouts/default/Default.vue"),
    children: [
      {
        path: "/api",
        name: "API",
        component: () =>
          import(/* webpackChunkName: "api" */ "@/views/API.vue"),
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL), //process.env.BASE_URL),
  routes,
});

export default router;
