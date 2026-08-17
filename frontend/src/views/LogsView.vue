<script setup lang="ts">
import { shallowRef, onMounted, onUnmounted, ref } from 'vue'
import { RefreshRight } from '@element-plus/icons-vue'
import { api } from '@/api/client'

interface LogEntry {
  time: string
  level: string
  message: string
}

const logs = ref<LogEntry[]>([])
const loading = shallowRef(false)
const autoScroll = shallowRef(true)
let timer: ReturnType<typeof setInterval> | null = null

async function load() {
  loading.value = true
  try {
    const res = await api.getLogs()
    logs.value = res
  } catch {
    /* ignore */
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  timer = setInterval(load, 5000)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1 class="page-title">日志</h1>
      <el-button :icon="RefreshRight" @click="load">刷新</el-button>
    </div>

    <div class="card log-card">
      <el-scrollbar height="calc(100vh - 160px)">
        <div v-if="logs.length === 0" class="empty">暂无日志</div>
        <div v-for="(l, i) in logs" :key="i" class="log-line">
          <span class="log-time mono">{{ l.time }}</span>
          <span class="log-level" :class="'lv-' + (l.level || 'info')">{{ l.level }}</span>
          <span class="log-msg">{{ l.message }}</span>
        </div>
      </el-scrollbar>
    </div>
  </div>
</template>

<style scoped>
.log-card {
  padding: 12px;
}
.log-line {
  display: flex;
  gap: 12px;
  font-size: 13px;
  padding: 3px 0;
  border-bottom: 1px solid var(--border);
  font-family: 'SF Mono', Menlo, Consolas, monospace;
}
.log-time {
  color: var(--text-dim);
  min-width: 90px;
}
.log-level {
  min-width: 60px;
  text-transform: uppercase;
  font-weight: 600;
}
.lv-error { color: var(--bad); }
.lv-warn { color: var(--warn); }
.lv-info { color: var(--accent); }
.log-msg {
  flex: 1;
  word-break: break-all;
}
.empty {
  color: var(--text-dim);
  padding: 40px;
  text-align: center;
}
</style>
