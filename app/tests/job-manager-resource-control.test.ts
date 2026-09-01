import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import type { JobRecord } from '../src/shared/contracts'
import type { StudioDatabase } from '../src/main/database'
import { EngineWorkerPool } from '../src/main/engine-worker-pool'
import { JobManager } from '../src/main/job-manager'
import { ResourceScheduler } from '../src/main/resource-scheduler'
import type { SecretStore } from '../src/main/secret-store'

function record(id: string, status: JobRecord['status'] = 'queued'): JobRecord {
  return {
    id,
    kind: 'scan',
    title: id,
    status,
    stage: status,
    progress: 0,
    completedItems: 0,
    totalItems: 0,
    config: {},
    createdAt: '2026-01-01T00:00:00.000Z',
    updatedAt: '2026-01-01T00:00:00.000Z',
  }
}

function databaseDouble() {
  const store = new Map<string, JobRecord>()
  return {
    store,
    database: {
      listJobs: () => [...store.values()],
      getJob: (id: string) => store.get(id),
      upsertJob: (job: JobRecord) => { store.set(job.id, structuredClone(job)) },
    } as unknown as StudioDatabase,
  }
}

describe('JobManager queued controls', () => {
  let directory = ''
  beforeEach(() => { directory = mkdtempSync(join(tmpdir(), 'mel-job-manager-')) })
  afterEach(() => { rmSync(directory, { recursive: true, force: true }) })

  function managerFixture() {
    const { store, database } = databaseDouble()
    const resources = new ResourceScheduler(join(directory, 'resources.json'))
    resources.updatePreferences({ cpuMaxConcurrent: 1 })
    resources.reserve(record('occupied', 'running'))
    const secrets = { resolveEnvironment: async () => ({}) } as unknown as SecretStore
    const manager = new JobManager(database, secrets, resources, new EngineWorkerPool())
    return { manager, store, resources }
  }

  it('pauses a queued job immediately without reserving a resource', async () => {
    const { manager, store, resources } = managerFixture()
    const created = manager.create({ kind: 'scan', title: 'queued scan', config: {} })
    await Promise.resolve()
    expect(store.get(created.id)?.status).toBe('queued')
    const paused = manager.control(created.id, 'pause')
    expect(paused.status).toBe('paused')
    expect(paused.stage).toContain('no resources reserved')
    expect(resources.hasReservation(created.id)).toBe(false)
  })

  it('cancels a queued job immediately instead of leaving a cancelling state', async () => {
    const { manager, store, resources } = managerFixture()
    const created = manager.create({ kind: 'scan', title: 'queued scan', config: {} })
    await Promise.resolve()
    const cancelled = manager.control(created.id, 'cancel')
    expect(cancelled.status).toBe('cancelled')
    expect(store.get(created.id)?.status).toBe('cancelled')
    expect(resources.hasReservation(created.id)).toBe(false)
  })
})
