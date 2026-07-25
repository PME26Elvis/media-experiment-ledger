import { createHash } from 'node:crypto'
import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process'
import { dirname } from 'node:path'
import { createInterface, type Interface } from 'node:readline'
import { app } from 'electron'
import type { EngineEvent } from './engine'
import { engineSourceRoot, packagedEngineExecutable } from './engine'

interface ActiveRequest {
  resolve: (value: Record<string, unknown>) => void
  reject: (error: Error) => void
  onEvent: (event: EngineEvent) => void
  signal: AbortSignal
  abort: () => void
  settled: boolean
  idleSeconds: number
}

function developmentPython(): string {
  if (process.env.MEL_PYTHON) return process.env.MEL_PYTHON
  return process.platform === 'win32' ? 'python' : 'python3'
}

function environmentFingerprint(environment: Record<string, string>): string {
  const payload = Object.entries(environment).sort(([left], [right]) => left.localeCompare(right))
  return createHash('sha256').update(JSON.stringify(payload)).digest('hex').slice(0, 16)
}

class PersistentEngineWorker {
  readonly createdAt = new Date().toISOString()
  lastUsedAt = this.createdAt
  private readonly child: ChildProcessWithoutNullStreams
  private readonly stdout: Interface
  private active?: ActiveRequest
  private idleTimer?: NodeJS.Timeout
  private destroyed = false

  constructor(
    readonly key: string,
    environment: Record<string, string>,
    private readonly onDestroyed: (worker: PersistentEngineWorker) => void,
  ) {
    const executable = app.isPackaged ? packagedEngineExecutable() : developmentPython()
    const args = app.isPackaged ? [] : ['-m', 'mel_engine']
    const cwd = app.isPackaged ? dirname(executable) : engineSourceRoot()
    const env = app.isPackaged
      ? { ...process.env, ...environment, MEL_ENGINE_PERSISTENT: '1' }
      : {
          ...process.env,
          ...environment,
          MEL_ENGINE_PERSISTENT: '1',
          PYTHONPATH: engineSourceRoot(),
        }
    this.child = spawn(executable, args, {
      cwd,
      env,
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
      shell: false,
    })
    this.stdout = createInterface({ input: this.child.stdout })
    this.stdout.on('line', line => this.handleLine(line))
    this.child.stderr.on('data', chunk => {
      this.active?.onEvent({ type: 'log', message: String(chunk).trim() })
    })
    this.child.on('error', error => this.fail(error))
    this.child.on('exit', code => {
      if (this.active && !this.active.settled) this.finishFailure(new Error(`Persistent engine exited with code ${code ?? 'unknown'}`), false)
      this.destroyed = true
      this.cleanup()
    })
  }

  get busy(): boolean { return Boolean(this.active) }

  execute(
    payload: Record<string, unknown>,
    onEvent: (event: EngineEvent) => void,
    signal: AbortSignal,
    idleSeconds: number,
  ): Promise<Record<string, unknown>> {
    if (this.destroyed) return Promise.reject(new Error('Persistent engine worker is closed.'))
    if (this.active) return Promise.reject(new Error('Persistent engine worker is already executing a request.'))
    if (this.idleTimer) clearTimeout(this.idleTimer)
    return new Promise((resolve, reject) => {
      const abort = () => {
        this.finishFailure(new Error('Engine request aborted'), false)
        this.destroy()
      }
      const request: ActiveRequest = { resolve, reject, onEvent, signal, abort, settled: false, idleSeconds }
      this.active = request
      signal.addEventListener('abort', abort, { once: true })
      try {
        this.child.stdin.write(`${JSON.stringify(payload)}\n`)
      } catch (error) {
        this.finishFailure(error instanceof Error ? error : new Error(String(error)))
      }
      this.lastUsedAt = new Date().toISOString()
    })
  }

  destroy(): void {
    if (this.destroyed) return
    this.destroyed = true
    if (this.idleTimer) clearTimeout(this.idleTimer)
    if (this.active && !this.active.settled) this.finishFailure(new Error('Persistent engine worker closed.'), false)
    this.stdout.close()
    this.child.kill()
    this.cleanup()
  }

  private handleLine(line: string): void {
    const request = this.active
    if (!request) return
    try {
      const event = JSON.parse(line) as EngineEvent
      request.onEvent(event)
      if (event.type === 'result') this.finishSuccess(event.data ?? {})
      if (event.type === 'error') this.finishFailure(new Error(event.message ?? 'Engine error'))
    } catch {
      request.onEvent({ type: 'log', message: line })
    }
  }

  private finishSuccess(result: Record<string, unknown>): void {
    const request = this.active
    if (!request || request.settled) return
    request.settled = true
    request.signal.removeEventListener('abort', request.abort)
    this.active = undefined
    this.lastUsedAt = new Date().toISOString()
    request.resolve(result)
    this.scheduleIdle(request.idleSeconds)
  }

  private finishFailure(error: Error, scheduleIdle = true): void {
    const request = this.active
    if (!request || request.settled) return
    request.settled = true
    request.signal.removeEventListener('abort', request.abort)
    this.active = undefined
    this.lastUsedAt = new Date().toISOString()
    request.reject(error)
    if (scheduleIdle) this.scheduleIdle(request.idleSeconds)
  }

  private fail(error: Error): void {
    this.finishFailure(error, false)
    this.destroy()
  }

  private scheduleIdle(idleSeconds: number): void {
    if (this.idleTimer) clearTimeout(this.idleTimer)
    if (idleSeconds <= 0 || this.destroyed) {
      if (idleSeconds <= 0 && !this.busy) this.destroy()
      return
    }
    this.idleTimer = setTimeout(() => {
      if (!this.busy) this.destroy()
    }, idleSeconds * 1000)
    this.idleTimer.unref()
  }

  private cleanup(): void {
    if (this.destroyed) this.onDestroyed(this)
  }
}

export interface EngineWorkerPoolSnapshot {
  workers: Array<{
    key: string
    busy: boolean
    createdAt: string
    lastUsedAt: string
  }>
}

export class EngineWorkerPool {
  private readonly workers = new Map<string, Set<PersistentEngineWorker>>()

  run(
    poolKey: string,
    payload: Record<string, unknown>,
    onEvent: (event: EngineEvent) => void,
    signal: AbortSignal,
    environment: Record<string, string>,
    idleSeconds: number,
  ): Promise<Record<string, unknown>> {
    const key = `${poolKey}:env-${environmentFingerprint(environment)}`
    const group = this.workers.get(key) ?? new Set<PersistentEngineWorker>()
    this.workers.set(key, group)
    let worker = [...group].find(candidate => !candidate.busy)
    if (!worker) {
      worker = new PersistentEngineWorker(key, environment, destroyed => {
        group.delete(destroyed)
        if (group.size === 0) this.workers.delete(key)
      })
      group.add(worker)
    }
    return worker.execute(payload, onEvent, signal, idleSeconds)
  }

  destroyAll(): void {
    for (const group of this.workers.values()) for (const worker of group) worker.destroy()
    this.workers.clear()
  }

  snapshot(): EngineWorkerPoolSnapshot {
    return {
      workers: [...this.workers.values()].flatMap(group => [...group].map(worker => ({
        key: worker.key,
        busy: worker.busy,
        createdAt: worker.createdAt,
        lastUsedAt: worker.lastUsedAt,
      }))),
    }
  }
}

export function detectionWorkerKey(config: Record<string, unknown>): string {
  return [
    'detection',
    String(config.model_sha256 ?? config.model_path ?? 'model'),
    String(config.execution_provider ?? 'cpu'),
    String(config.device_id ?? 0),
    String(config.coreml_compute_units ?? 'ALL'),
    String(config.allow_provider_fallback ?? true),
  ].join(':')
}
