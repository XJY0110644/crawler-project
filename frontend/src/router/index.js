import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import Repos from '../views/Repos.vue'
import Articles from '../views/Articles.vue'
import Tasks from '../views/Tasks.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/dashboard', component: Dashboard },
    { path: '/repos', component: Repos },
    { path: '/articles', component: Articles },
    { path: '/tasks', component: Tasks },
  ],
})

export default router