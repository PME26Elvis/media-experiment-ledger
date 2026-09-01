export const HARDWARE_IPC = {
  snapshot: 'mel:hardware-snapshot',
  selfTest: 'mel:hardware-self-test',
  preferencesGet: 'mel:hardware-preferences-get',
  preferencesSet: 'mel:hardware-preferences-set',
  clearCache: 'mel:hardware-clear-cache',
  exportEvidence: 'mel:hardware-export-evidence',
} as const

export type HardwareProviderKey = 'cpu' | 'directml' | 'cuda' | 'coreml'
export type CoreMlComputeUnits = 'ALL' | 'CPU_ONLY' | 'CPU_AND_GPU' | 'CPU_AND_NE'

export interface HardwareProviderSupport {
  provider: string
  available: boolean
}

export interface EngineProviderInventory {
  schema_version: number
  runtime_version: string
  runtime_device: string
  platform: string
  machine: string
  available_providers: string[]
  provider_support: Record<HardwareProviderKey, HardwareProviderSupport>
  distributions: Record<string, string>
  host_memory?: { total_bytes: number; available_bytes: number }
  cpu?: { logical_cores: number; processor: string }
}

export interface HardwareGpuDevice {
  id: number
  active: boolean
  vendorId?: number
  deviceId?: number
  vendor?: string
  name?: string
  driverVendor?: string
  driverVersion?: string
  driverDate?: string
  cudaComputeCapability?: string
}

export interface HardwareSnapshot {
  schemaVersion: 1
  capturedAt: string
  platform: NodeJS.Platform
  arch: string
  cpu: {
    model: string
    logicalCores: number
  }
  memory: {
    totalBytes: number
    freeBytes: number
  }
  gpuFeatureStatus: Record<string, string>
  gpuDevices: HardwareGpuDevice[]
  auxiliaryAttributes: Record<string, unknown>
  engineReady: boolean
  engineProviders?: EngineProviderInventory
  warnings: string[]
}

export interface HardwarePreferences {
  provider: HardwareProviderKey
  deviceId: number
  allowCpuFallback: boolean
  coremlComputeUnits: CoreMlComputeUnits
}

export interface HardwareSelfTestRequest extends HardwarePreferences {
  warmRuns?: number
}

export interface HardwareSelfTestResult {
  schema_version: number
  requested_provider: HardwareProviderKey
  requested_provider_name: string
  active_provider?: string
  device_id: number
  allow_cpu_fallback: boolean
  coreml_compute_units: CoreMlComputeUnits
  runtime_version?: string
  available_providers?: string[]
  registered: boolean
  session_created: boolean
  cold_start_ms?: number
  cold_inference_ms?: number
  warm_inference_ms?: number
  warm_runs?: number
  profile_provider_nodes?: Record<string, number>
  assigned_node_count: number
  cpu_assigned_node_count: number
  fallback_detected: boolean
  cache?: { path?: string; size_bytes: number; file_count: number }
  passed: boolean
  status: 'passed' | 'fallback' | 'unavailable' | 'error'
  recommendation?: string
  error?: { name: string; message: string }
  created_at: string
}

export interface HardwareCacheResult {
  cleared: boolean
  path: string
  removedBytes: number
}

export interface HardwareEvidenceExport {
  path: string
  sha256: string
  sizeBytes: number
}

export interface HardwareApi {
  snapshot(refresh?: boolean): Promise<HardwareSnapshot>
  selfTest(request: HardwareSelfTestRequest): Promise<HardwareSelfTestResult>
  preferences: {
    get(): Promise<HardwarePreferences>
    set(patch: Partial<HardwarePreferences>): Promise<HardwarePreferences>
  }
  clearCache(provider: HardwareProviderKey): Promise<HardwareCacheResult>
  exportEvidence(outputDirectory: string, selfTest?: HardwareSelfTestResult): Promise<HardwareEvidenceExport>
}
