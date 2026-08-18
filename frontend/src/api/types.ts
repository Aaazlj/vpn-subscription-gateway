export interface VpnNode {
  id: string
  hostname: string
  ip: string
  score: string
  ping: string
  speed: string
  country_long: string
  country_short: string
  sessions: string
  uptime: string
  users: string
  traffic: string
  message: string
  lat: number
  lng: number
  latency_ms: number | null
  reachable: boolean
  ip_type: string
  openvpn_config: string
}

export interface CountryEntry {
  code: string
  count: number
}

export type CountriesResponse = CountryEntry[]

export interface TunnelInfo {
  index: number
  node_id: string
  label: string
  country: string
  tun: string
  table: number
  port: number
  alive: boolean
  exit_ip: string
  last_error: string
  started_at: number
  latency_ms: number | null
}

export interface TunnelsSummary {
  total: number
  alive: number
  tunnels: TunnelInfo[]
}

export interface SystemCheck {
  openvpn: boolean
  iproute2: boolean
  tun_device: boolean
  root: boolean | null
}

export interface GatewayConfig {
  web_user: string
  web_pass: string
  proxy_user: string
  proxy_pass: string
  proxy_host: string
  proxy_port_base: number
  max_tunnels: number
  fetch_interval: number
  check_interval: number
  sub_token: string
  [key: string]: unknown
}

export interface StatusResponse {
  selected: string[]
  tunnels: TunnelsSummary
  public_ip: string
  system: SystemCheck
  config: GatewayConfig
}

export interface NodesResponse {
  total: number
  nodes: VpnNode[]
}
