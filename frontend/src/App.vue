<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  Monitor, Connection, Link, Document, Setting, SwitchButton,
} from '@element-plus/icons-vue'
import { useStatusStore } from '@/stores/status'
import { logout } from '@/router'
import { isLoggedIn } from '@/api/client'

const route = useRoute()
const status = useStatusStore()

const activeMenu = computed(() => route.path)
const showLayout = computed(() => route.name !== 'login' && isLoggedIn())

const navItems = [
  { path: '/nodes', label: '节点管理', icon: Monitor },
  { path: '/tunnels', label: '隧道状态', icon: Connection },
  { path: '/subscribe', label: '订阅链接', icon: Link },
  { path: '/logs', label: '日志', icon: Document },
  { path: '/settings', label: '设置', icon: Setting },
]

onMounted(() => {
  status.load().catch(() => {})
  status.startPolling(4000)
})

onUnmounted(() => {
  status.stopPolling()
})
</script>

<template>
  <el-container v-if="showLayout" class="app-shell">
    <el-aside width="200px" class="sidebar">
      <div class="brand">
        <span class="brand-dot" />
        <span class="brand-name">VPN 订阅网关</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        class="side-menu"
      >
        <el-menu-item
          v-for="item in navItems"
          :key="item.path"
          :index="item.path"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>

      <div class="side-logout">
        <el-button text :icon="SwitchButton" @click="logout">登出</el-button>
      </div>
      <div class="side-footer">
        <div class="ip-line">
          <span class="ip-label">出口 IP</span>
          <span class="mono ip-value">{{ status.publicIp || '—' }}</span>
        </div>
        <div class="tunnel-line">
          <span class="dot" :class="{ ok: status.tunnels.alive > 0 }" />
          <span>隧道 {{ status.tunnels.alive }}/{{ status.tunnels.total }} 在线</span>
        </div>
      </div>
    </el-aside>

    <el-main class="main">
      <router-view />
    </el-main>
  </el-container>
  <router-view v-if="!showLayout" />
</template>

<style scoped>
.app-shell {
  height: 100vh;
  overflow: hidden;
}
.sidebar {
  background: var(--panel);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
}
.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 18px 16px;
  font-weight: 700;
  font-size: 15px;
}
.brand-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 8px var(--accent);
}
.side-menu {
  flex: 1;
  border-right: none;
  background: transparent;
}
.side-logout {
  padding: 4px 8px;
}
.side-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--border);
  font-size: 12px;
  color: var(--text-dim);
}
.ip-line {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 8px;
}
.ip-label {
  color: var(--text-dim);
}
.ip-value {
  color: var(--accent);
  word-break: break-all;
}
.tunnel-line {
  display: flex;
  align-items: center;
  gap: 6px;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--bad);
}
.dot.ok {
  background: var(--ok);
}
.main {
  background: var(--bg);
  padding: 0;
  overflow-y: auto;
}
</style>
