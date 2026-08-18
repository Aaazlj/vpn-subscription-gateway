import { shallowRef, ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/api/client'
import type {
  StatusResponse,
  TunnelsSummary,
  GatewayConfig,
  SystemCheck,
} from '@/api/types'

export const useStatusStore = defineStore('status', () => {
  const status = shallowRef<StatusResponse | null>(null)
  const selected = shallowRef<string[]>([])
  const tunnels = shallowRef<TunnelsSummary>({ total: 0, alive: 0, tunnels: [] })
  const publicIp = ref('')
  const system = shallowRef<SystemCheck | null>(null)
  const config = shallowRef<GatewayConfig | null>(null)
  const polling = ref(false)
  let timer: ReturnType<typeof setInterval> | null = null

  async function load() {
    const s = await api.getStatus()
    status.value = s
    selected.value = s.selected
    tunnels.value = s.tunnels
    publicIp.value = s.public_ip
    system.value = s.system
    config.value = s.config
    return s
  }

  function startPolling(intervalMs = 4000) {
    if (timer) clearInterval(timer)
    timer = setInterval(async () => {
      try {
        const s = await api.getStatus()
        selected.value = s.selected
        tunnels.value = s.tunnels
        publicIp.value = s.public_ip
        config.value = s.config
        status.value = s
      } catch {
        /* transient poll failure, ignore */
      }
    }, intervalMs)
    polling.value = true
  }

  function stopPolling() {
    if (timer) clearInterval(timer)
    timer = null
    polling.value = false
  }

  async function toggleNode(nodeId: string, action: 'add' | 'remove' | 'toggle' = 'toggle') {
    const res = await api.selectNode(nodeId, 'toggle')
    selected.value = res.selected
    return res
  }

  async function selectByCountry(country: string, limit: number) {
    const res = await api.selectCountry(country, limit)
    selected.value = res.selected
    return res
  }

  async function reconnectAll() {
    await api.reconnectAll()
  }

  return {
    status, selected, tunnels, publicIp, system, config,
    load, startPolling, stopPolling, toggleNode, selectByCountry, reconnectAll,
  }
})
