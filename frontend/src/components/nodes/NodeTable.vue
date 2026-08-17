<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import type { VpnNode } from '@/api/types'
import { useStatusStore } from '@/stores/status'

const props = defineProps<{
  nodes: VpnNode[]
  loading: boolean
}>()

const status = useStatusStore()

const selectedSet = computed(() => new Set(status.selected))

function countryFlag(code: string): string {
  if (!code) return ''
  const cc = code.toUpperCase()
  const base = 127397
  const codePoints = [...cc].map((c) => base + c.charCodeAt(0))
  return String.fromCodePoint(...codePoints)
}

function fmtLatency(ms: number | null): string {
  if (ms === null || ms === undefined) return '—'
  return ms < 1000 ? ms + ' ms' : (ms / 1000).toFixed(1) + ' s'
}

async function onToggle(node: VpnNode) {
  try {
    await status.toggleNode(node.id)
    ElMessage.success(selectedSet.value.has(node.id) ? '已加入选择' : '已取消选择')
  } catch (e) {
    ElMessage.error(String((e as Error).message ?? e))
  }
}
</script>

<template>
  <el-table
    v-loading="props.loading"
    :data="props.nodes"
    stripe
    height="100%"
    empty-text="暂无节点,点击右上角「拉取节点」"
  >
    <el-table-column label="国家" width="90">
      <template #default="{ row }">
        <span>{{ countryFlag(row.country_short) }} {{ row.country_short }}</span>
      </template>
    </el-table-column>
    <el-table-column label="主机名" min-width="180" show-overflow-tooltip>
      <template #default="{ row }">{{ row.hostname }}</template>
    </el-table-column>
    <el-table-column prop="ip" label="IP" width="150">
      <template #default="{ row }"><span class="mono">{{ row.ip }}</span></template>
    </el-table-column>
    <el-table-column label="延迟" width="100" sortable :sort-method="(a: VpnNode, b: VpnNode) => (a.latency_ms ?? Infinity) - (b.latency_ms ?? Infinity)">
      <template #default="{ row }">
        <el-tag
          :type="row.reachable ? (row.latency_ms && row.latency_ms < 300 ? 'success' : 'warning') : 'info'"
          size="small"
          disable-transitions
        >
          {{ fmtLatency(row.latency_ms) }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column prop="score" label="评分" width="110" sortable />
    <el-table-column label="当前在线" width="100" sortable :sort-method="(a: VpnNode, b: VpnNode) => Number(a.sessions) - Number(b.sessions)">
      <template #default="{ row }">{{ row.sessions || '—' }}</template>
    </el-table-column>
    <el-table-column label="状态" width="90">
      <template #default="{ row }">
        <el-tag :type="row.reachable ? 'success' : 'danger'" size="small" disable-transitions>
          {{ row.reachable ? '可达' : '不可达' }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="110" fixed="right">
      <template #default="{ row }">
        <el-button
          :type="selectedSet.has(row.id) ? 'danger' : 'primary'"
          size="small"
          @click="onToggle(row)"
        >
          {{ selectedSet.has(row.id) ? '取消' : '选择' }}
        </el-button>
      </template>
    </el-table-column>
  </el-table>
</template>
