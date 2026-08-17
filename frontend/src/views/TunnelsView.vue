<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { RefreshRight } from '@element-plus/icons-vue'
import { useStatusStore } from '@/stores/status'

const status = useStatusStore()

const tunnels = computed(() => status.tunnels.tunnels)

function fmtTime(ts: number): string {
  if (!ts) return '—'
  return new Date(ts * 1000).toLocaleTimeString()
}

async function onReconnect() {
  try {
    await status.reconnectAll()
    ElMessage.success('已触发重连')
  } catch (e) {
    ElMessage.error(String((e as Error).message ?? e))
  }
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1 class="page-title">隧道状态</h1>
      <el-button type="primary" :icon="RefreshRight" @click="onReconnect">重连全部</el-button>
    </div>

    <div class="card">
      <el-descriptions :column="3" border>
        <el-descriptions-item label="隧道总数">{{ status.tunnels.total }}</el-descriptions-item>
        <el-descriptions-item label="在线隧道">
          <el-tag :type="status.tunnels.alive > 0 ? 'success' : 'danger'" size="small">
            {{ status.tunnels.alive }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="服务器出口 IP">
          <span class="mono">{{ status.publicIp }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="OpenVPN">
          <el-tag :type="status.system?.openvpn ? 'success' : 'danger'" size="small">
            {{ status.system?.openvpn ? '已安装' : '缺失' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="TUN 设备">
          <el-tag :type="status.system?.tun_device ? 'success' : 'danger'" size="small">
            {{ status.system?.tun_device ? '可用' : '缺失' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="运行权限">
          <el-tag :type="status.system?.root ? 'success' : 'warning'" size="small">
            {{ status.system?.root ? 'root' : '非 root' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </div>

    <div class="card">
      <el-table :data="tunnels" stripe empty-text="暂无隧道,请先在「节点管理」选择节点">
        <el-table-column prop="label" label="节点" min-width="200" show-overflow-tooltip />
        <el-table-column prop="tun" label="接口" width="90">
          <template #default="{ row }"><span class="mono">{{ row.tun }}</span></template>
        </el-table-column>
        <el-table-column prop="port" label="代理端口" width="100">
          <template #default="{ row }"><span class="mono">{{ row.port }}</span></template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.alive ? 'success' : 'danger'" size="small" disable-transitions>
              {{ row.alive ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="exit_ip" label="出口 IP" width="150">
          <template #default="{ row }"><span class="mono">{{ row.exit_ip || '—' }}</span></template>
        </el-table-column>
        <el-table-column label="建立时间" width="110">
          <template #default="{ row }">{{ fmtTime(row.started_at) }}</template>
        </el-table-column>
        <el-table-column prop="last_error" label="错误" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.last_error || '—' }}</template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>
