import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import type { JobRecord } from '../src/shared/contracts'
import {
  classifyOutOfMemory,
  estimateJobResource,
  normalizeSchedulerPreferences,
  ResourceScheduler,
} from '../src/main/resource-scheduler'

function job(id: string, config: Record<string, unknown> = {}, kind: JobRecord['kind'] = 'detection'): JobRecord {
  return {
    id,
    kind,
    title: id,
    status: 'queued',
    stage: 'queued',
    progress: 0,
    completedItems: 0,
    totalItems: 0,
    config,
    createdAt: '2026-01-01T00:00:00.000Z',
    updatedAt: '2026-01-01T00:00:00.000Z',
  }
}

describe('ResourceScheduler', () => {
  let directory = ''
  beforeEach(() => { directory = mkdtempSync(join(tmpdir(), 'mel-resource-scheduler-')) })
  afterEach(() => { rmSync(directory, { recursive: true, force: true }) })

  it('estimates accelerator memory from model input dimensions', () => {
    const request = estimateJobResource(job('gpu', {
      execution_provider: 'cuda',
      device_id: 2,
      input_width: 640,
      input_height: 640,
    }))
    expect(request.resourceKey).toBe('cuda:2')
    expect(request.accelerator).toBe(true)
    expect(request.estimateSource).toBe('model-input')
    expect(request.estimatedMemoryMb).toBeGreaterThan(800)
  })

  it('uses an explicit memory estimate when a job provides one', () => {
    const request = estimateJobResource(job('gpu', {
      execution_provider: 'directml',
      estimated_vram_mb: 1536,
    }))
    expect(request.estimatedMemoryMb).toBe(1536)
    expect(request.estimateSource).toBe('explicit')
  })

  it('blocks a second job when provider-device concurrency is full and admits it after release', () => {
    const scheduler = new ResourceScheduler(join(directory, 'preferences.json'))
    const first = job('first', { execution_provider: 'coreml', device_id: 0, estimated_vram_mb: 512 })
    const second = job('second', { execution_provider: 'coreml', device_id: 0, estimated_vram_mb: 512 })
    scheduler.reserve(first)
    const blocked = scheduler.assess(second)
    expect(blocked.admitted).toBe(false)
    expect(blocked.reason).toContain('concurrency')
    scheduler.release(first.id)
    expect(scheduler.assess(second).admitted).toBe(true)
  })

  it('keeps the configured accelerator safety reserve available', () => {
    const scheduler = new ResourceScheduler(join(directory, 'preferences.json'))
    scheduler.updatePreferences({
      defaultAcceleratorPolicy: { maxConcurrent: 4, memoryBudgetMb: 2048, safetyReserveMb: 512 },
    })
    scheduler.reserve(job('first', { execution_provider: 'cuda', estimated_vram_mb: 1024 }))
    const blocked = scheduler.assess(job('second', { execution_provider: 'cuda', estimated_vram_mb: 600 }))
    expect(blocked.admitted).toBe(false)
    expect(blocked.capacity.availableMemoryMb).toBe(512)
    expect(blocked.reason).toContain('safety reserve')
  })

  it('normalizes unsafe persisted values and device policy keys', () => {
    const normalized = normalizeSchedulerPreferences({
      cpuMaxConcurrent: 999,
      warmSessionIdleSeconds: -10,
      defaultAcceleratorPolicy: { maxConcurrent: 0, memoryBudgetMb: 100, safetyReserveMb: 999 },
      devicePolicies: {
        'cuda:0': { maxConcurrent: 2, memoryBudgetMb: 8192, safetyReserveMb: 1024 },
        invalid: { maxConcurrent: 10, memoryBudgetMb: 9999, safetyReserveMb: 1 },
      },
    })
    expect(normalized.cpuMaxConcurrent).toBe(64)
    expect(normalized.warmSessionIdleSeconds).toBe(0)
    expect(normalized.defaultAcceleratorPolicy.memoryBudgetMb).toBe(256)
    expect(normalized.defaultAcceleratorPolicy.safetyReserveMb).toBeLessThanOrEqual(128)
    expect(Object.keys(normalized.devicePolicies)).toEqual(['cuda:0'])
  })

  it('clamps a fallback safety reserve when a malformed policy lowers the memory budget', () => {
    const normalized = normalizeSchedulerPreferences({
      defaultAcceleratorPolicy: { maxConcurrent: 1, memoryBudgetMb: 256 },
    })
    expect(normalized.defaultAcceleratorPolicy.memoryBudgetMb).toBe(256)
    expect(normalized.defaultAcceleratorPolicy.safetyReserveMb).toBe(128)
  })

  it('classifies accelerator OOM with actionable recovery', () => {
    const request = estimateJobResource(job('gpu', { execution_provider: 'cuda' }))
    const result = classifyOutOfMemory(new Error('CUDA out of memory allocating tensor'), request)
    expect(result.category).toBe('accelerator-out-of-memory')
    expect(result.message).toContain('Reduce the model input size')
    expect(result.message).toContain('CPU fallback')
  })
})
