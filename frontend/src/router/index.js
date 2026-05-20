import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue')
  },
  {
    path: '/trending',
    name: 'Trending',
    component: () => import('../views/Trending.vue')
  },
  {
    path: '/analyze',
    name: 'Analyze',
    component: () => import('../views/Analyze.vue')
  },
  {
    path: '/signals',
    name: 'Signals',
    component: () => import('../views/Signals.vue')
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('../views/Chat.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
