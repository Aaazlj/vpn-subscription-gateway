import { createRouter, createWebHashHistory } from 'vue-router'
import NodesView from '@/views/NodesView.vue'
import TunnelsView from '@/views/TunnelsView.vue'
import SubscribeView from '@/views/SubscribeView.vue'
import LogsView from '@/views/LogsView.vue'
import SettingsView from '@/views/SettingsView.vue'
import LoginView from '@/views/LoginView.vue'
import { isLoggedIn, clearToken } from '@/api/client'

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/login', name: 'login', component: LoginView, meta: { public: true } },
    { path: '/', redirect: '/nodes' },
    { path: '/nodes', name: 'nodes', component: NodesView, meta: { title: '节点管理' } },
    { path: '/tunnels', name: 'tunnels', component: TunnelsView, meta: { title: '隧道状态' } },
    { path: '/subscribe', name: 'subscribe', component: SubscribeView, meta: { title: '订阅链接' } },
    { path: '/logs', name: 'logs', component: LogsView, meta: { title: '日志' } },
    { path: '/settings', name: 'settings', component: SettingsView, meta: { title: '设置' } },
  ],
})

router.beforeEach((to, _from, next) => {
  if (to.meta.public) {
    if (to.name === 'login' && isLoggedIn()) {
      next('/nodes')
    } else {
      next()
    }
  } else if (!isLoggedIn()) {
    next('/login')
  } else {
    next()
  }
})

export function logout() {
  clearToken()
  router.push('/login')
}
