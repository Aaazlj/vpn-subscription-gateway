<script setup lang="ts">
import { shallowRef, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { RefreshRight, Download, Cpu } from '@element-plus/icons-vue'
import NodeTable from '@/components/nodes/NodeTable.vue'
import NodeFilters from '@/components/nodes/NodeFilters.vue'
import { useNodesStore, useCountriesStore } from '@/stores/nodes'
import { useStatusStore } from '@/stores/status'

const nodesStore = useNodesStore()
const countries = useCountriesStore()
const status = useStatusStore()

const keyword = shallowRef('')
const country = shallowRef('')
const onlyReachable = shallowRef(false)
const page = shallowRef(1)
const pageSize = shallowRef(20)

const autoCountry = shallowRef('')
const autoLimit = shallowRef(3)

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  const cc = country.value.toUpperCase()
  const reach = onlyReachable.value
  return nodesStore.nodes.filter((n) => {
    if (cc && n.country_short !== cc) return false
    if (reach && !n.reachable) return false
    if (kw && !(n.hostname.toLowerCase().includes(kw) || n.ip.includes(kw))) return false
    return true
  })
})

const paged = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filtered.value.slice(start, start + pageSize.value)
})

async function loadNodes() {
  await Promise.all([nodesStore.fetchNodes(), countries.load(true)])
}

async function onRefresh() {
  try {
    await nodesStore.refreshFromUpstream()
    await nodesStore.fetchNodes()
    ElMessage.success('已从 VPNGate 重新拉取节点')
  } catch (e) {
    ElMessage.error(String((e as Error).message ?? e))
  }
}

async function onAutoSelect() {
  if (!autoCountry.value) {
    ElMessage.warning('请先选择国家')
    return
  }
  try {
    await status.selectByCountry(autoCountry.value, autoLimit.value)
    ElMessage.success('已自动挑选 ' + autoLimit.value + ' 个 ' + autoCountry.value + ' 节点')
  } catch (e) {
    ElMessage.error(String((e as Error).message ?? e))
  }
}

watch([keyword, country, onlyReachable], () => {
  page.value = 1
})

onMounted(loadNodes)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1 class="page-title">节点管理</h1>
      <div class="actions">
        <el-button :icon="RefreshRight" @click="loadNodes">刷新列表</el-button>
        <el-button type="primary" :icon="Download" :loading="nodesStore.loading" @click="onRefresh">
          拉取节点
        </el-button>
      </div>
    </div>

    <div class="card">
      <NodeFilters
        v-model:keyword="keyword"
        v-model:country="country"
        v-model:only-reachable="onlyReachable"
      />
    </div>

    <div class="card">
      <div class="auto-select">
        <span class="auto-label">自动挑选:</span>
        <el-select v-model="autoCountry" placeholder="选择国家" filterable class="auto-country">
          <el-option
            v-for="(count, code) in countries.countries"
            :key="code"
            :label="code + ' (' + count + ')'"
            :value="code"
          />
        </el-select>
        <el-select v-model="autoLimit" class="auto-limit">
          <el-option v-for="n in 8" :key="n" :label="n + ' 个'" :value="n" />
        </el-select>
        <el-button type="success" :icon="Cpu" @click="onAutoSelect">按国家自选</el-button>
      </div>
    </div>

    <div class="card table-card">
      <NodeTable :nodes="paged" :loading="nodesStore.loading" />
      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="filtered.length"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.actions {
  display: flex;
  gap: 10px;
}
.auto-select {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}
.auto-label {
  color: var(--text-dim);
}
.auto-country {
  width: 200px;
}
.auto-limit {
  width: 100px;
}
.table-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.pager {
  display: flex;
  justify-content: flex-end;
}
</style>
