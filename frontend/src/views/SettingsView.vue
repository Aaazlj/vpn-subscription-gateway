<script setup lang="ts">
import { shallowRef, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { useStatusStore } from '@/stores/status'
import type { GatewayConfig } from '@/api/types'

const status = useStatusStore()

const form = shallowRef<Partial<GatewayConfig>>({})
const saving = shallowRef(false)

const proxyUrl = computed(() => {
  const host = status.publicIp || '服务器IP'
  const port = form.value.proxy_port_base || 10000
  return 'socks5://' + form.value.proxy_user + ':' + form.value.proxy_pass + '@' + host + ':' + port
})

onMounted(async () => {
  const cfg = await api.getConfig()
  form.value = { ...cfg }
})

async function save() {
  saving.value = true
  try {
    const payload: Record<string, unknown> = {}
    const fields = ['web_user', 'web_pass', 'proxy_user', 'proxy_pass', 'proxy_port_base', 'max_tunnels', 'sub_token']
    for (const f of fields) {
      const v = (form.value as Record<string, unknown>)[f]
      if (v !== undefined && v !== null && v !== '') payload[f] = v
    }
    await api.updateConfig(payload)
    await status.load()
    ElMessage.success('配置已保存并生效')
  } catch (e) {
    ElMessage.error(String((e as Error).message ?? e))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1 class="page-title">设置</h1>
      <el-button type="primary" :loading="saving" @click="save">保存配置</el-button>
    </div>

    <div class="card">
      <h2 class="section-title">Web 面板登录</h2>
      <el-form label-width="140px" class="form">
        <el-form-item label="用户名">
          <el-input v-model="form.web_user" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.web_pass" type="password" show-password />
        </el-form-item>
      </el-form>
    </div>

    <div class="card">
      <h2 class="section-title">代理认证</h2>
      <el-form label-width="140px" class="form">
        <el-form-item label="代理用户名">
          <el-input v-model="form.proxy_user" />
        </el-form-item>
        <el-form-item label="代理密码">
          <el-input v-model="form.proxy_pass" type="password" show-password />
        </el-form-item>
        <el-form-item label="代理起始端口">
          <el-input-number v-model="form.proxy_port_base" :min="1" :max="65500" />
        </el-form-item>
      </el-form>
      <p class="hint">单节点代理示例: <span class="mono">{{ proxyUrl }}</span></p>
    </div>

    <div class="card">
      <h2 class="section-title">隧道与订阅</h2>
      <el-form label-width="140px" class="form">
        <el-form-item label="最大隧道数">
          <el-input-number v-model="form.max_tunnels" :min="1" :max="32" />
        </el-form-item>
        <el-form-item label="订阅 Token">
          <el-input v-model="form.sub_token" placeholder="留空则订阅无需 token" />
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.section-title {
  font-size: 16px;
  margin: 0 0 12px;
}
.form {
  max-width: 520px;
}
.hint {
  color: var(--text-dim);
  font-size: 12px;
  word-break: break-all;
}
</style>
