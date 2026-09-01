import { randomUUID } from 'node:crypto'
import { app } from 'electron'
import type { CreateJobRequest, JobRecord } from '../shared/contracts'
import type { ResourceSchedulerPreferences, ResourceSchedulerSnapshot } from '../shared/resource-scheduler-contracts'
import { StudioDatabase } from './database'
import { detectionWorkerKey, EngineWorkerPool } from './engine-worker-pool'
import { resetEngineProviderInventory, runEngine, type EngineEvent } from './engine'
import { classifyOutOfMemory, ResourceScheduler, schedulerPreferencesPath } from './resource-scheduler'
import { SecretStore } from './secret-store'

const ACTIVE_STATUSES = new Set<JobRecord['status']>(['queued', 'running', 'pausing', 'cancelling'])

export class JobManager {
  private readonly controllers = new Map<string, AbortController>()
  private dispatching = false

  constructor(
    private readonly db: StudioDatabase,
    private readonly secrets: SecretStore,
    private readonly resources = new ResourceScheduler(schedulerPreferencesPath(app.getPath('userData'))),
    private readonly workers = new EngineWorkerPool(),
  ) {
    this.resources.setChangedCallback(() => { void this.dispatch() })
    this.resources.setQueuedJobs(this.list())
  }

  list(): JobRecord[] {
    return this.db.listJobs()
  }

  activeCount(): number {
    return this.list().filter(job => ACTIVE_STATUSES.has(job.status)).length
  }

  resourceSnapshot(): ResourceSchedulerSnapshot {
    return { ...this.resources.snapshot(), warmWorkers: this.workers.snapshot().workers }
  }

  resourcePreferences(): ResourceSchedulerPreferences {
    return this.resources.preferences()
  }

  updateResourcePreferences(patch: Partial<ResourceSchedulerPreferences>): ResourceSchedulerPreferences {
    return this.resources.updatePreferences(patch)
  }

  resetEngineRuntime(): void {
    if (this.activeCount() > 0) throw new Error('Pause or finish active and queued jobs before switching the engine runtime.')
    this.workers.destroyAll()
    resetEngineProviderInventory()
  }

  create(request: CreateJobRequest): JobRecord {
    const now = new Date().toISOString()
    const job: JobRecord = {
      id: randomUUID(),
      kind: request.kind,
      title: request.title,
      status: 'queued',
      stage: 'queued · evaluating resource budget',
      progress: 0,
      completedItems: 0,
      totalItems: 0,
      config: request.config,
      createdAt: now,
      updatedAt: now,
    }
    this.db.upsertJob(job)
    this.resources.setQueuedJobs(this.list())
    void this.dispatch()
    return job
  }

  async dispatch(): Promise<void> {
    if (this.dispatching) return
    this.dispatching = true
    try {
      while (true) {
        const queued = this.list()
          .filter(job => job.status === 'queued' && !this.controllers.has(job.id) && !this.resources.hasReservation(job.id))
          .sort((left, right) => left.createdAt.localeCompare(right.createdAt))
        this.resources.setQueuedJobs(queued)
        let started = false
        for (const job of queued) {
          const decision = this.resources.assess(job)
          if (!decision.admitted) {
            const stage = `queued · ${decision.reason ?? 'waiting for resources'}`
            if (job.stage !== stage) this.save({ ...job, stage })
            continue
          }
          this.resources.reserve(job)
          started = true
          void this.startReserved(job)
        }
        if (!started) break
        await Promise.resolve()
      }
    } finally {
      this.resources.setQueuedJobs(this.list())
      this.dispatching = false
    }
  }

  private async startReserved(job: JobRecord): Promise<void> {
    if (this.controllers.has(job.id)) return
    const controller = new AbortController()
    this.controllers.set(job.id, controller)
    this.save({ ...job, status: 'running', stage: 'starting · resource reserved', error: undefined })
    const request = this.resources.assess(job).request
    try {
      const profileId = typeof job.config.credential_profile_id === 'string'
        ? job.config.credential_profile_id
        : undefined
      const environment = await this.secrets.resolveEnvironment(profileId)
      const payload = { operation: job.kind, job_id: job.id, ...job.config }
      const onEvent = (event: EngineEvent) => {
        const current = this.db.getJob(job.id) ?? job
        if (event.type === 'progress') {
          this.save({
            ...current,
            status: 'running',
            stage: event.stage ?? current.stage,
            progress: Math.max(0, Math.min(100, event.progress ?? current.progress)),
            completedItems: event.completed ?? current.completedItems,
            totalItems: event.total ?? current.totalItems,
          })
        }
      }
      const output = job.kind === 'detection'
        ? await this.workers.run(
            detectionWorkerKey(job.config),
            payload,
            onEvent,
            controller.signal,
            environment,
            this.resources.preferences().warmSessionIdleSeconds,
          )
        : await runEngine(payload, onEvent, controller.signal, environment)
      const current = this.db.getJob(job.id) ?? job
      this.save({ ...current, status: 'completed', stage: 'verified · resources released', progress: 100, output, error: undefined })
    } catch (error) {
      const current = this.db.getJob(job.id) ?? job
      const cancelled = controller.signal.aborted
      const interrupted = current.status === 'recoverable' && current.stage.startsWith('interrupted')
      const classification = classifyOutOfMemory(error, request)
      this.save(interrupted ? current : {
        ...current,
        status: cancelled ? (current.status === 'pausing' ? 'paused' : 'cancelled') : 'recoverable',
        stage: cancelled
          ? (current.status === 'pausing' ? 'paused · accelerator process released' : 'cancelled · resources released')
          : classification.matched ? classification.category ?? 'failed' : 'failed',
        error: cancelled ? undefined : classification.message,
      })
    } finally {
      this.controllers.delete(job.id)
      this.resources.release(job.id)
      this.resources.setQueuedJobs(this.list())
      void this.dispatch()
    }
  }

  control(id: string, action: 'pause' | 'resume' | 'cancel'): JobRecord {
    const job = this.db.getJob(id)
    if (!job) throw new Error('Job not found')
    const active = this.controllers.has(id)
    if (action === 'cancel') {
      if (!active) {
        const next = { ...job, status: 'cancelled' as const, stage: 'cancelled · removed from queue' }
        this.save(next)
        this.resources.release(id)
        this.resources.setQueuedJobs(this.list())
        void this.dispatch()
        return next
      }
      const next = { ...job, status: 'cancelling' as const, stage: 'cancelling · releasing process and accelerator memory' }
      this.save(next)
      this.controllers.get(id)?.abort()
      return next
    }
    if (action === 'pause') {
      if (!active) {
        const next = { ...job, status: 'paused' as const, stage: 'paused · no resources reserved' }
        this.save(next)
        this.resources.release(id)
        this.resources.setQueuedJobs(this.list())
        void this.dispatch()
        return next
      }
      const next = { ...job, status: 'pausing' as const, stage: 'checkpointing · releasing process and accelerator memory' }
      this.save(next)
      this.controllers.get(id)?.abort()
      return next
    }
    if (job.status === 'paused' || job.status === 'recoverable' || job.status === 'failed') {
      const next = { ...job, status: 'queued' as const, stage: 'queued · evaluating resource budget', error: undefined }
      this.save(next)
      this.resources.setQueuedJobs(this.list())
      void this.dispatch()
      return next
    }
    return job
  }

  async pauseAll(): Promise<void> {
    for (const job of this.list().filter(item => jobIsActive(item))) {
      this.control(job.id, 'pause')
    }
    const deadline = Date.now() + 15_000
    while (this.activeCount() > 0 && Date.now() < deadline) {
      await new Promise(resolve => setTimeout(resolve, 100))
    }
    if (this.activeCount() > 0) throw new Error('Some jobs could not checkpoint before maintenance.')
  }

  recoverInterruptedJobs(): number {
    let recovered = 0
    for (const job of this.list()) {
      if (ACTIVE_STATUSES.has(job.status)) {
        this.resources.release(job.id)
        this.save({ ...job, status: 'recoverable', stage: 'interrupted · resources released', error: 'The application exited while this job was active. Resume to reuse durable checkpoints.' })
        recovered += 1
      }
    }
    this.resources.setQueuedJobs(this.list())
    this.shutdown()
    return recovered
  }

  shutdown(): void {
    for (const controller of this.controllers.values()) controller.abort()
    this.controllers.clear()
    this.workers.destroyAll()
    for (const job of this.list()) this.resources.release(job.id)
  }

  private save(job: JobRecord): void {
    this.db.upsertJob({ ...job, updatedAt: new Date().toISOString() })
  }
}

function jobIsActive(job: JobRecord): boolean {
  return job.status === 'running' || job.status === 'queued'
}
