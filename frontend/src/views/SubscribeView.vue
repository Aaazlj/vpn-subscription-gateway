<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument } from '@element-plus/icons-vue'
import { useStatusStore } from '@/stores/status'

const status = useStatusStore()

const base = computed(() => {
  const host = window.location.host
  const token = status.config?.sub_token || ''
  return { host, token }
})

function subUrl(fmt: string): string {
  const token = base.value.token
  const suffix = token ? '?token=' + encodeURIComponent(token) : ''
  return window.location.origin + '/sub/' + fmt + suffix
}

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.warning('复制失败,请手动复制')
  }
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1 class="page-title">订阅链接</h1>
    </div>

    <div class="card">
      <p class="hint">
        把下面任一订阅链接导入客户端(Clash / v2rayN 等)即可使用。链接指向本机
        <span class="mono">{{ status.publicIp || '…' }}</span>
        上已建立的 SOCKS5 代理隧道。
      </p>

      <div class="sub-row" v-for="fmt in ['clash', 'v2ray', 'base64']" :key="fmt">
        <div class="sub-label">{{ fmt }}</div>
        <el-input :model-value="subUrl(fmt)" readonly class="sub-input">
          <template #append>
            <el-button :icon="CopyDocument" @click="copy(subUrl(fmt))">复制</el-button>
          </template>
        </el-input>
      </div>
    </div>

    <div class="card">
      <p class="hint">当前已选节点对应的代理端口:</p>
      <el-table :data="status.tunnels.tunnels" stripe empty-text="暂无在线隧道">
        <el-table-column prop="label" label="节点" min-width="200" />
        <el-table-column prop="port" label="SOCKS5 端口" width="140">
          <template #default="{ row }">
            <span class="mono">{{ status.publicIp }}:{{ row.port }}</span>
          </template>
        </el-table-column>
        <el-table-column label="认证" width="200">
          <template #default>
            <span class="mono">{{ status.config?.proxy_user }}:{{ status.config?.proxy_pass }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<style scoped>
.hint {
  color: var(--text-dim);
  margin: 0 0 16px;
  line-height: 1.6;
}
.sub-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.sub-label {
  width: 60px;
  font-weight: 600;
  text-transform: uppercase;
}
.sub-input {
  flex: 1;
}
</style>
