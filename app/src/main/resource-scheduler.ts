import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import type { JobRecord } from '../shared/contracts'
import type {
  DeviceResourcePolicy,
  JobResourceRequest,
  QueueDecision,
  ResourceReservation,
  ResourceSchedulerPreferences,
  ResourceSchedulerSnapshot,
} from '../shared/resource-scheduler-contracts'

const DEFAULT_ACCELERATOR_POLICY: DeviceResourcePolicy = {
  maxConcurrent: 1,
  memoryBudgetMb: 4096,
  safetyReserveMb: 512,
}

export const DEFAULT_RESOURCE_SCHEDULER_PREFERENCES: ResourceSchedulerPreferences = {
  cpuMaxConcurrent: 2,
  warmSessionIdleSeconds: 90,
  defaultAcceleratorPolicy: DEFAULT_ACCELERATOR_POLICY,
  devicePolicies: {},
}

function finiteInteger(value: unknown, fallback: number, minimum: number, maximum: number): number {
  return typeof value === 'number' && Number.isFinite(value)
    ? Math.max(minimum, Math.min(maximum, Math.trunc(value)))
    : fallback
}

function normalizePolicy(value: unknown, fallback: DeviceResourcePolicy): DeviceResourcePolicy {
  const record = value && typeof value === 'object' ? value as Record<string, unknown> : {}
  const memoryBudgetMb = finiteInteger(record.memoryBudgetMb, fallback.memoryBudgetMb, 256, 262_144)
  return {
    maxConcurrent: finiteInteger(record.maxConcurrent, fallback.maxConcurrent, 1, 32),
    memoryBudgetMb,
    safetyReserveMb: finiteInteger(record.safetyReserveMb, fallback.safetyReserveMb, 0, Math.max(0, memoryBudgetMb - 128)),
  }
}

export function normalizeSchedulerPreferences(value: unknown): ResourceSchedulerPreferences {
  const record = value && typeof value === 'object' ? value as Record<string, unknown> : {}
  const defaultAcceleratorPolicy = normalizePolicy(record.defaultAcceleratorPolicy, DEFAULT_ACCELERATOR_POLICY)
  const rawPolicies = record.devicePolicies && typeof record.devicePolicies === 'object'
    ? record.devicePolicies as Record<string, unknown>
    : {}
  const devicePolicies = Object.fromEntries(Object.entries(rawPolicies)
    .filter(([key]) => /^(?:directml|cuda|coreml):\d+$/u.test(key))
    .map(([key, policy]) => [key, normalizePolicy(policy, defaultAcceleratorPolicy)]))
  return {
    cpuMaxConcurrent: finiteInteger(record.cpuMaxConcurrent, 2, 1, 64),
    warmSessionIdleSeconds: finiteInteger(record.warmSessionIdleSeconds, 90, 0, 3600),
    defaultAcceleratorPolicy,
    devicePolicies,
  }
}

function providerKey(job: JobRecord): string {
  const raw = String(job.config.execution_provider ?? 'cpu').toLowerCase()
  return ['directml', 'cuda', 'coreml'].includes(raw) ? raw : 'cpu'
}

function estimateDetectionMemoryMb(job: JobRecord): number {
  const width = finiteInteger(job.config.input_width, 640, 32, 16_384)
  const height = finiteInteger(job.config.input_height, 640, 32, 16_384)
  const batch = finiteInteger(job.config.batch_size, 1, 1, 64)
  const pixels = width * height * batch
  const baseMb = 256
  const activationMb = pixels * 0.0015
  const outputMb = finiteInteger(job.config.max_detections, 300, 1, 100_000) * 0.002
  return Math.max(384, Math.ceil(baseMb + activationMb + outputMb))
}

export function estimateJobResource(job: JobRecord): JobResourceRequest {
  const provider = providerKey(job)
  const accelerator = provider !== 'cpu'
  const deviceId = accelerator ? finiteInteger(job.config.device_id, 0, 0, 64) : 0
  const explicit = typeof job.config.estimated_vram_mb === 'number' && Number.isFinite(job.config.estimated_vram_mb)
    ? Math.max(1, Math.trunc(job.config.estimated_vram_mb))
    : undefined
  let estimatedMemoryMb = 0
  let estimateSource: JobResourceRequest['estimateSource'] = 'job-default'
  if (accelerator && explicit) {
    estimatedMemoryMb = explicit
    estimateSource = 'explicit'
  } else if (accelerator && job.kind === 'detection') {
    estimatedMemoryMb = estimateDetectionMemoryMb(job)
    estimateSource = 'model-input'
  } else if (accelerator) {
    estimatedMemoryMb = job.kind === 'atlas' ? 768 : job.kind === 'automation' ? 512 : 384
  }
  return {
    jobId: job.id,
    jobKind: job.kind,
    resourceKey: accelerator ? `${provider}:${deviceId}` : 'cpu',
    provider,
    deviceId,
    accelerator,
    estimatedMemoryMb,
    estimateSource,
  }
}

export interface OutOfMemoryClassification {
  matched: boolean
  category?: 'accelerator-out-of-memory' | 'host-out-of-memory'
  message: string
}

export function classifyOutOfMemory(error: unknown, request: JobResourceRequest): OutOfMemoryClassification {
  const raw = error instanceof Error ? error.message : String(error)
  const normalized = raw.toLowerCase()
  const acceleratorMatch = /(?:cuda|directml|coreml|gpu|device).{0,40}(?:out of memory|allocation|resource exhausted)|(?:out of memory|allocation failed).{0,40}(?:cuda|gpu|device)/u.test(normalized)
  const hostMatch = /memoryerror|cannot allocate memory|javascript heap out of memory|std::bad_alloc/u.test(normalized)
  if (acceleratorMatch) {
    return {
      matched: true,
      category: 'accelerator-out-of-memory',
      message: `Accelerator memory was exhausted on ${request.resourceKey}. Reduce the model input size or batch, lower the device concurrency budget, or rerun with explicit CPU fallback. Original error: ${raw}`,
    }
  }
  if (hostMatch) {
    return {
      matched: true,
      category: 'host-out-of-memory',
      message: `Host memory was exhausted. Reduce corpus parallelism or input size and retry after closing other memory-heavy applications. Original error: ${raw}`,
    }
  }
  return { matched: false, message: raw }
}

export class ResourceScheduler {
  private preferencesValue: ResourceSchedulerPreferences
  private readonly reservations = new Map<string, ResourceReservation>()
  private queuedJobs: JobRecord[] = []
  private changed?: () => void

  constructor(private readonly preferencesPath: string) {
    this.preferencesValue = this.load()
  }

  setChangedCallback(callback: () => void): void {
    this.changed = callback
  }

  preferences(): ResourceSchedulerPreferences {
    return structuredClone(this.preferencesValue)
  }

  updatePreferences(patch: Partial<ResourceSchedulerPreferences>): ResourceSchedulerPreferences {
    this.preferencesValue = normalizeSchedulerPreferences({ ...this.preferencesValue, ...patch })
    mkdirSync(dirname(this.preferencesPath), { recursive: true })
    writeFileSync(this.preferencesPath, `${JSON.stringify(this.preferencesValue, null, 2)}\n`, 'utf8')
    this.changed?.()
    return this.preferences()
  }

  setQueuedJobs(jobs: JobRecord[]): void {
    this.queuedJobs = jobs.filter(job => job.status === 'queued')
  }

  assess(job: JobRecord): QueueDecision {
    const request = estimateJobResource(job)
    const matching = [...this.reservations.values()].filter(item => item.resourceKey === request.resourceKey)
    if (!request.accelerator) {
      const maxConcurrent = this.preferencesValue.cpuMaxConcurrent
      const activeConcurrent = matching.length
      return {
        admitted: activeConcurrent < maxConcurrent,
        reason: activeConcurrent >= maxConcurrent
          ? `Waiting for a CPU slot (${activeConcurrent}/${maxConcurrent} active).`
          : undefined,
        request,
        capacity: {
          maxConcurrent,
          activeConcurrent,
          memoryBudgetMb: 0,
          safetyReserveMb: 0,
          reservedMemoryMb: 0,
          availableMemoryMb: 0,
        },
      }
    }
    const policy = this.policyFor(request.resourceKey)
    const reservedMemoryMb = matching.reduce((sum, item) => sum + item.estimatedMemoryMb, 0)
    const availableMemoryMb = Math.max(0, policy.memoryBudgetMb - policy.safetyReserveMb - reservedMemoryMb)
    const activeConcurrent = matching.length
    const slotAvailable = activeConcurrent < policy.maxConcurrent
    const memoryAvailable = request.estimatedMemoryMb <= availableMemoryMb
    let reason: string | undefined
    if (!slotAvailable) reason = `Waiting for ${request.resourceKey}: concurrency is ${activeConcurrent}/${policy.maxConcurrent}.`
    else if (!memoryAvailable) reason = `Waiting for ${request.resourceKey}: needs about ${request.estimatedMemoryMb} MB, but ${availableMemoryMb} MB remains after the ${policy.safetyReserveMb} MB safety reserve.`
    return {
      admitted: slotAvailable && memoryAvailable,
      reason,
      request,
      capacity: {
        maxConcurrent: policy.maxConcurrent,
        activeConcurrent,
        memoryBudgetMb: policy.memoryBudgetMb,
        safetyReserveMb: policy.safetyReserveMb,
        reservedMemoryMb,
        availableMemoryMb,
      },
    }
  }

  reserve(job: JobRecord): ResourceReservation {
    const decision = this.assess(job)
    if (!decision.admitted) throw new Error(decision.reason ?? 'Resource request was not admitted.')
    const reservation: ResourceReservation = { ...decision.request, reservedAt: new Date().toISOString() }
    this.reservations.set(job.id, reservation)
    this.changed?.()
    return reservation
  }

  release(jobId: string): void {
    if (this.reservations.delete(jobId)) this.changed?.()
  }

  hasReservation(jobId: string): boolean {
    return this.reservations.has(jobId)
  }

  snapshot(): ResourceSchedulerSnapshot {
    const queued = this.queuedJobs.map(job => ({
      jobId: job.id,
      title: job.title,
      status: job.status,
      stage: job.stage,
      decision: this.assess(job),
    }))
    const keys = new Set<string>(['cpu', ...Object.keys(this.preferencesValue.devicePolicies)])
    for (const item of this.reservations.values()) keys.add(item.resourceKey)
    for (const item of queued) keys.add(item.decision.request.resourceKey)
    const resources = [...keys].sort().map(resourceKey => {
      const synthetic = {
        id: `snapshot-${resourceKey}`,
        kind: 'detection',
        title: resourceKey,
        status: 'queued',
        stage: 'queued',
        progress: 0,
        completedItems: 0,
        totalItems: 0,
        config: resourceKey === 'cpu' ? { execution_provider: 'cpu' } : {
          execution_provider: resourceKey.split(':')[0],
          device_id: Number(resourceKey.split(':')[1] ?? 0),
          estimated_vram_mb: 1,
        },
        createdAt: '', updatedAt: '',
      } as JobRecord
      const decision = this.assess(synthetic)
      return {
        resourceKey,
        provider: decision.request.provider,
        deviceId: decision.request.deviceId,
        accelerator: decision.request.accelerator,
        ...decision.capacity,
      }
    })
    return {
      schemaVersion: 1,
      capturedAt: new Date().toISOString(),
      preferences: this.preferences(),
      reservations: [...this.reservations.values()].map(value => ({ ...value })),
      queued,
      resources,
    }
  }

  private policyFor(resourceKey: string): DeviceResourcePolicy {
    return this.preferencesValue.devicePolicies[resourceKey] ?? this.preferencesValue.defaultAcceleratorPolicy
  }

  private load(): ResourceSchedulerPreferences {
    if (!existsSync(this.preferencesPath)) return structuredClone(DEFAULT_RESOURCE_SCHEDULER_PREFERENCES)
    try {
      return normalizeSchedulerPreferences(JSON.parse(readFileSync(this.preferencesPath, 'utf8')))
    } catch {
      return structuredClone(DEFAULT_RESOURCE_SCHEDULER_PREFERENCES)
    }
  }
}

export function schedulerPreferencesPath(userDataPath: string): string {
  return join(userDataPath, 'resource-scheduler-preferences.json')
}
