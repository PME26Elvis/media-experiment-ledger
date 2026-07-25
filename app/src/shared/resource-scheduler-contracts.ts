import type { JobKind, JobRecord } from './contracts'

export const RESOURCE_SCHEDULER_IPC = {
  snapshot: 'mel:resource-scheduler-snapshot',
  preferencesGet: 'mel:resource-scheduler-preferences-get',
  preferencesSet: 'mel:resource-scheduler-preferences-set',
} as const

export interface DeviceResourcePolicy {
  maxConcurrent: number
  memoryBudgetMb: number
  safetyReserveMb: number
}

export interface ResourceSchedulerPreferences {
  cpuMaxConcurrent: number
  warmSessionIdleSeconds: number
  defaultAcceleratorPolicy: DeviceResourcePolicy
  devicePolicies: Record<string, DeviceResourcePolicy>
}

export interface JobResourceRequest {
  jobId: string
  jobKind: JobKind
  resourceKey: string
  provider: string
  deviceId: number
  accelerator: boolean
  estimatedMemoryMb: number
  estimateSource: 'explicit' | 'model-input' | 'job-default'
}

export interface ResourceReservation extends JobResourceRequest {
  reservedAt: string
}

export interface QueueDecision {
  admitted: boolean
  reason?: string
  request: JobResourceRequest
  capacity: {
    maxConcurrent: number
    activeConcurrent: number
    memoryBudgetMb: number
    safetyReserveMb: number
    reservedMemoryMb: number
    availableMemoryMb: number
  }
}

export interface ResourceSchedulerSnapshot {
  schemaVersion: 1
  capturedAt: string
  preferences: ResourceSchedulerPreferences
  reservations: ResourceReservation[]
  queued: Array<{
    jobId: string
    title: string
    status: JobRecord['status']
    stage: string
    decision: QueueDecision
  }>
  resources: Array<{
    resourceKey: string
    provider: string
    deviceId: number
    accelerator: boolean
    maxConcurrent: number
    activeConcurrent: number
    memoryBudgetMb: number
    safetyReserveMb: number
    reservedMemoryMb: number
    availableMemoryMb: number
  }>
}

export interface ResourceSchedulerApi {
  snapshot(): Promise<ResourceSchedulerSnapshot>
  preferences: {
    get(): Promise<ResourceSchedulerPreferences>
    set(patch: Partial<ResourceSchedulerPreferences>): Promise<ResourceSchedulerPreferences>
  }
}
