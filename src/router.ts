import { createRouter, createWebHistory } from "vue-router";
export const router = createRouter({
  history: createWebHistory(),
  scrollBehavior(to, from, saved) {
    if (saved) return saved;
    if (to.path === from.path) return;
    return { top: 0 };
  },
  routes: [
    { path: '/streaming', component: () => import('./pages/StreamingPage.vue') },
    { path: '/streaming/anime/:animeId', component: () => import('./pages/StreamingPage.vue') },
    { path: '/streaming/episode/:episodeId', component: () => import('./pages/StreamingPage.vue') },
    { path: "/", component: () => import("./pages/HomePage.vue") },
    { path: "/anime", component: () => import("./pages/AnimePage.vue") },
    {
      path: "/anime/:id(\\d+)",
      component: () => import("./pages/DetailPage.vue"),
    },
    {
      path: "/watch/:id(\\d+)/:episode(\\d+)",
      component: () => import("./pages/WatchPage.vue"),
    },
    { path: "/watchlist", component: () => import("./pages/LibraryPage.vue") },
    { path: "/history", component: () => import("./pages/LibraryPage.vue") },
    { path: "/schedule", component: () => import("./pages/SchedulePage.vue") },
    { path: "/settings", component: () => import("./pages/SettingsPage.vue") },
    {
      path: "/:pathMatch(.*)*",
      component: () => import("./pages/NotFoundPage.vue"),
    },
  ],
});
