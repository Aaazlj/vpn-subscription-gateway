<script setup lang="ts">
import { shallowRef, computed } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { useCountriesStore } from '@/stores/nodes'

const props = defineProps<{
  keyword: string
  country: string
  onlyReachable: boolean
}>()

const emit = defineEmits<{
  'update:keyword': [value: string]
  'update:country': [value: string]
  'update:onlyReachable': [value: boolean]
}>()

const countriesStore = useCountriesStore()

const countryOptions = computed(() =>
  countriesStore.list
    .map((entry) => ({ code: entry.code, count: entry.count }))
    .sort((a, b) => b.count - a.count),
)

function onKeyword(v: string | undefined | null) {
  emit("update:keyword", v || "")
  emit('update:keyword', v)
}
function onCountry(v: string) {
  emit('update:country', v)
}
function onReachable(v: boolean | string | number) {
  emit('update:onlyReachable', Boolean(v))
}
</script>

<template>
  <div class="filters">
    <el-input
      :model-value="props.keyword"
      class="kw"
      placeholder="搜索主机名 / IP"
      clearable
      :prefix-icon="Search"
      @update:model-value="onKeyword"
    />
    <el-select
      :model-value="props.country"
      class="country"
      placeholder="全部国家"
      clearable
      filterable
      @update:model-value="onCountry"
    >
      <el-option
        v-for="opt in countryOptions"
        :key="opt.code"
        :label="opt.code + ' (' + opt.count + ')'"
        :value="opt.code"
      />
    </el-select>
    <el-checkbox
      :model-value="props.onlyReachable"
      label="仅显示可达"
      @update:model-value="onReachable"
    />
  </div>
</template>

<style scoped>
.filters {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}
.kw {
  width: 240px;
}
.country {
  width: 200px;
}
</style>
