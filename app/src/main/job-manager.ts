import { randomUUID } from 'node:crypto'
import type { CreateJobRequest, JobRecord } from '../shared/contracts'
import { StudioDatabase } from './database'
import { runEngine } from './engine'
import { SecretStore } from './secret-store'

const ACTIVE_STATUSES = new Set<JobRecord['status']>(['queued', 'running', 'pausing', 'cancelling'])

export class JobManager {
  private readonly controllers = new Map<string, AbortController>()

  constructor(
    private readonly db: StudioDatabase,
    private readonly secrets: SecretStore,
  ) {}

  list(): JobRecord[] {
    return this.db.listJobs()
  }

  activeCount(): number {
    return this.list().filter(job => ACTIVE_STATUSES.has(job.status)).length
  }

  create(request: CreateJobRequest): JobRecord {
    const now = new Date().toISOString()
    const job: JobRecord = {
      id: randomUUID(),
      kind: request.kind,
      title: request.title,
      status: 'queued',
      stage: 'queued',
      progress: 0,
      completedItems: 0,
      totalItems: 0,
      config: request.config,
      createdAt: now,
      updatedAt: now,
    }
    this.db.upsertJob(job)
    void this.start(job)
    return job
  }

  async start(job: JobRecord): Promise<void> {
    if (this.controllers.has(job.id)) return
    const controller = new AbortController()
    this.controllers.set(job.id, controller)
    this.save({ ...job, status: 'running', stage: 'starting', error: undefined })
    try {
      const profileId = typeof job.config.credential_profile_id === 'string'
        ? job.config.credential_profile_id
        : undefined
      const environment = await this.secrets.resolveEnvironment(profileId)
      const output = await runEngine(
        { operation: job.kind, job_id: job.id, ...job.config },
        event => {
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
        },
        controller.signal,
        environment,
      )
      const current = this.db.getJob(job.id) ?? job
      this.save({ ...current, status: 'completed', stage: 'verified', progress: 100, output, error: undefined })
    } catch (error) {
      const current = this.db.getJob(job.id) ?? job
      const cancelled = controller.signal.aborted
      this.save({
        ...current,
        status: cancelled ? (current.status === 'pausing' ? 'paused' : 'cancelled') : 'recoverable',
        stage: cancelled ? (current.status === 'pausing' ? 'paused' : 'cancelled') : 'failed',
        error: cancelled ? undefined : error instanceof Error ? error.message : String(error),
      })
    } finally {
      this.controllers.delete(job.id)
    }
  }

  control(id: string, action: 'pause' | 'resume' | 'cancel'): JobRecord {
    const job = this.db.getJob(id)
    if (!job) throw new Error('Job not found')
    if (action === 'cancel') {
      const next = { ...job, status: 'cancelling' as const, stage: 'cancelling' }
      this.save(next)
      this.controllers.get(id)?.abort()
      return next
    }
    if (action === 'pause') {
      const next = { ...job, status: 'pausing' as const, stage: 'checkpointing' }
      this.save(next)
      this.controllers.get(id)?.abort()
      return next
    }
    if (job.status === 'paused' || job.status === 'recoverable' || job.status === 'failed') {
      const next = { ...job, status: 'queued' as const, stage: 'queued', error: undefined }
      this.save(next)
      void this.start(next)
      return next
    }
    return job
  }

  async pauseAll(): Promise<void> {
    for (const job of this.list().filter(item => item.status === 'running' || item.status === 'queued')) {
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
        this.save({ ...job, status: 'recoverable', stage: 'interrupted', error: 'The application exited while this job was active. Resume to reuse durable checkpoints.' })
        recovered += 1
      }
    }
    return recovered
  }

  private save(job: JobRecord): void {
    this.db.upsertJob({ ...job, updatedAt: new Date().toISOString() })
  }
}
