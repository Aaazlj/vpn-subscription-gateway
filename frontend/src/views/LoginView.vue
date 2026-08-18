<script setup lang="ts">
import { shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { api, setToken } from '@/api/client'

const router = useRouter()
const username = shallowRef('')
const password = shallowRef('')
const loading = shallowRef(false)

async function onLogin() {
  if (!username.value || !password.value) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const res = await api.login(username.value, password.value)
    setToken(res.token, res.username)
    ElMessage.success('登录成功')
    router.push('/nodes')
  } catch (e) {
    ElMessage.error(String((e as Error).message ?? e))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="login-title">
        <span class="login-dot" />
        VPN 订阅网关
      </div>
      <el-form @submit.prevent="onLogin" class="login-form">
        <el-form-item>
          <el-input
            v-model="username"
            placeholder="用户名"
            :prefix-icon="User"
            size="large"
            @keyup.enter="onLogin"
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="password"
            type="password"
            placeholder="密码"
            :prefix-icon="Lock"
            size="large"
            show-password
            @keyup.enter="onLogin"
          />
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          class="login-btn"
          :loading="loading"
          @click="onLogin"
        >
          登录
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.login-wrap {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
}
.login-card {
  width: 380px;
  padding: 40px 32px;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 12px;
}
.login-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 28px;
  justify-content: center;
}
.login-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 10px var(--accent);
}
.login-btn {
  width: 100%;
  margin-top: 8px;
}
</style>
