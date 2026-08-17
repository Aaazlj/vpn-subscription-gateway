import { createRouter, createWebHashHistory } from 'vue-router'
import NodesView from '@/views/NodesView.vue'
import TunnelsView from '@/views/TunnelsView.vue'
import SubscribeView from '@/views/SubscribeView.vue'
import LogsView from '@/views/LogsView.vue'
import SettingsView from '@/views/SettingsView.vue'

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/nodes' },
    { path: '/nodes', name: 'nodes', component: NodesView, meta: { title: '节点管理' } },
    { path: '/tunnels', name: 'tunnels', component: TunnelsView, meta: { title: '隧道状态' } },
    { path: '/subscribe', name: 'subscribe', component: SubscribeView, meta: { title: '订阅链接' } },
    { path: '/logs', name: 'logs', component: LogsView, meta: { title: '日志' } },
    { path: '/settings', name: 'settings', component: SettingsView, meta: { title: '设置' } },
  ],
})
