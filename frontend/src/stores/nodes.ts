import { shallowRef, ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/api/client'
import type { VpnNode, CountriesResponse } from '@/api/types'

export const useNodesStore = defineStore('nodes', () => {
  const nodes = shallowRef<VpnNode[]>([])
  const loading = ref(false)
  const refreshedAt = ref<number | null>(null)

  async function fetchNodes(params?: { country?: string; reachable?: boolean }) {
    loading.value = true
    try {
      const res = await api.getNodes(params)
      nodes.value = res.nodes
      refreshedAt.value = Date.now()
      return res
    } finally {
      loading.value = false
    }
  }

  async function refreshFromUpstream() {
    loading.value = true
    try {
      const res = await api.refreshNodes()
      return res
    } finally {
      loading.value = false
    }
  }

  return { nodes, loading, refreshedAt, fetchNodes, refreshFromUpstream }
})

export const useCountriesStore = defineStore('countries', () => {
  const countries = shallowRef<CountriesResponse>({})
  let loaded = false

  async function load(force = false) {
    if (loaded && !force) return
    countries.value = await api.getCountries()
    loaded = true
  }

  return { countries, load }
})
