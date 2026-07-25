import { createHash } from 'node:crypto'
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs'
import { cpus, freemem, totalmem } from 'node:os'
import { join } from 'node:path'
import { app } from 'electron'
import type {
  HardwareCacheResult,
  HardwareEvidenceExport,
  HardwarePreferences,
  HardwareProviderKey,
  HardwareSelfTestRequest,
  HardwareSelfTestResult,
  HardwareSnapshot,
} from '../shared/hardware-contracts'
import { engineProviderInventory, engineReady, runEngine } from './engine'

const DEFAULT_PREFERENCES: HardwarePreferences = {
  provider: 'cpu',
  deviceId: 0,
  allowCpuFallback: true,
  coremlComputeUnits: 'ALL',
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? value as Record<string, unknown> : {}
}

function numeric(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined
}

function text(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value : undefined
}

function hashFile(path: string): string {
  return createHash('sha256').update(readFileSync(path)).digest('hex')
}

export class HardwareRuntimeManager {
  private readonly preferencesPath: string
  private snapshotPromise?: Promise<HardwareSnapshot>

  constructor(private readonly userDataPath: string) {
    this.preferencesPath = join(userDataPath, 'hardware-preferences.json')
  }

  preferences(): HardwarePreferences {
    if (!existsSync(this.preferencesPath)) return { ...DEFAULT_PREFERENCES }
    try {
      const parsed = asRecord(JSON.parse(readFileSync(this.preferencesPath, 'utf8')))
      const provider = ['cpu', 'directml', 'cuda', 'coreml'].includes(String(parsed.provider))
        ? parsed.provider as HardwareProviderKey
        : DEFAULT_PREFERENCES.provider
      const computeUnits = ['ALL', 'CPU_ONLY', 'CPU_AND_GPU', 'CPU_AND_NE'].includes(String(parsed.coremlComputeUnits))
        ? parsed.coremlComputeUnits as HardwarePreferences['coremlComputeUnits']
        : DEFAULT_PREFERENCES.coremlComputeUnits
      return {
        provider,
        deviceId: Math.max(0, Math.trunc(numeric(parsed.deviceId) ?? 0)),
        allowCpuFallback: typeof parsed.allowCpuFallback === 'boolean' ? parsed.allowCpuFallback : true,
        coremlComputeUnits: computeUnits,
      }
    } catch {
      return { ...DEFAULT_PREFERENCES }
    }
  }

  savePreferences(patch: Partial<HardwarePreferences>): HardwarePreferences {
    const current = this.preferences()
    const next: HardwarePreferences = {
      provider: patch.provider ?? current.provider,
      deviceId: Math.max(0, Math.trunc(patch.deviceId ?? current.deviceId)),
      allowCpuFallback: patch.allowCpuFallback ?? current.allowCpuFallback,
      coremlComputeUnits: patch.coremlComputeUnits ?? current.coremlComputeUnits,
    }
    mkdirSync(this.userDataPath, { recursive: true })
    writeFileSync(this.preferencesPath, `${JSON.stringify(next, null, 2)}\n`, 'utf8')
    return next
  }

  async snapshot(refresh = false): Promise<HardwareSnapshot> {
    if (refresh) {
      this.snapshotPromise = undefined
      await engineProviderInventory(true)
    }
    this.snapshotPromise ??= this.captureSnapshot()
    return this.snapshotPromise
  }

  private async captureSnapshot(): Promise<HardwareSnapshot> {
    const warnings: string[] = []
    let gpuInfo: Record<string, unknown> = {}
    let gpuFeatureStatus: Record<string, string> = {}
    try {
      gpuInfo = asRecord(await app.getGPUInfo('complete'))
      gpuFeatureStatus = app.getGPUFeatureStatus() as unknown as Record<string, string>
    } catch (error) {
      warnings.push(`Electron GPU inspection failed: ${error instanceof Error ? error.message : String(error)}`)
    }
    const rawDevices = Array.isArray(gpuInfo.gpuDevice) ? gpuInfo.gpuDevice : []
    const gpuDevices = rawDevices.map((value, id) => {
      const item = asRecord(value)
      return {
        id,
        active: Boolean(item.active),
        vendorId: numeric(item.vendorId),
        deviceId: numeric(item.deviceId),
        vendor: text(item.vendorString) ?? text(item.vendor),
        name: text(item.deviceString) ?? text(item.name),
        driverVendor: text(item.driverVendor),
        driverVersion: text(item.driverVersion),
        driverDate: text(item.driverDate),
        cudaComputeCapability: text(item.cudaComputeCapabilityMajor)
          ? `${String(item.cudaComputeCapabilityMajor)}.${String(item.cudaComputeCapabilityMinor ?? '0')}`
          : undefined,
      }
    })
    const engineProviders = await engineProviderInventory(true)
    if (!engineProviders) warnings.push('The packaged engine provider inventory is unavailable.')
    const processors = cpus()
    const { gpuDevice: _gpuDevice, ...auxiliaryAttributes } = gpuInfo
    return {
      schemaVersion: 1,
      capturedAt: new Date().toISOString(),
      platform: process.platform,
      arch: process.arch,
      cpu: { model: processors[0]?.model ?? 'unknown', logicalCores: processors.length },
      memory: { totalBytes: totalmem(), freeBytes: freemem() },
      gpuFeatureStatus,
      gpuDevices,
      auxiliaryAttributes,
      engineReady: await engineReady(),
      engineProviders,
      warnings,
    }
  }

  async selfTest(request: HardwareSelfTestRequest): Promise<HardwareSelfTestResult> {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 90_000)
    try {
      const result = await runEngine({
        operation: 'provider-self-test',
        provider: request.provider,
        device_id: request.deviceId,
        allow_cpu_fallback: request.allowCpuFallback,
        coreml_compute_units: request.coremlComputeUnits,
        warm_runs: request.warmRuns ?? 5,
      }, () => undefined, controller.signal)
      return result as unknown as HardwareSelfTestResult
    } finally {
      clearTimeout(timeout)
    }
  }

  clearCache(provider: HardwareProviderKey): HardwareCacheResult {
    const path = join(this.userDataPath, provider === 'coreml' ? 'models/.mel-provider-cache/coreml' : `.mel-provider-cache/${provider}`)
    let removedBytes = 0
    if (existsSync(path)) {
      const accumulate = (target: string): number => {
        try {
          const stat = statSync(target)
          if (stat.isFile()) return stat.size
          return readdirSync(target).reduce((total, item) => total + accumulate(join(target, item)), 0)
        } catch { return 0 }
      }
      removedBytes = accumulate(path)
      rmSync(path, { recursive: true, force: true })
    }
    return { cleared: true, path, removedBytes }
  }

  async exportEvidence(outputDirectory: string, selfTest?: HardwareSelfTestResult): Promise<HardwareEvidenceExport> {
    const directory = outputDirectory.trim()
    if (!directory) throw new Error('An output directory is required.')
    mkdirSync(directory, { recursive: true })
    const payload = {
      schemaVersion: 1,
      exportedAt: new Date().toISOString(),
      snapshot: await this.snapshot(true),
      preferences: this.preferences(),
      selfTest,
      privacy: {
        rawPathsIncluded: false,
        credentialsIncluded: false,
        mediaIncluded: false,
      },
    }
    const path = join(directory, `mel-hardware-evidence-${Date.now()}.json`)
    writeFileSync(path, `${JSON.stringify(payload, null, 2)}\n`, 'utf8')
    return { path, sha256: hashFile(path), sizeBytes: statSync(path).size }
  }
}
