import { createHash } from 'node:crypto'
import { app } from 'electron'
import { access } from 'node:fs/promises'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, isAbsolute, join, relative, resolve, sep } from 'node:path'
import { spawn } from 'node:child_process'
import { createInterface } from 'node:readline'

export interface EngineEvent {
  type: 'progress' | 'result' | 'error' | 'log'
  stage?: string
  progress?: number
  completed?: number
  total?: number
  data?: Record<string, unknown>
  message?: string
}

export interface EngineProviderInventory {
  schema_version: number
  runtime_version: string
  runtime_device: string
  platform: string
  machine: string
  available_providers: string[]
  provider_support: Record<string, { provider: string; available: boolean }>
  distributions: Record<string, string>
}

interface ActiveBundlePointer {
  schemaVersion: 1
  bundleId: string
  version: string
  entrypoint: string
  engineSha256: string
}

let providerInventoryPromise: Promise<EngineProviderInventory | undefined> | undefined
let activeEngineCache: { pointerMtime: number; executable?: string } | undefined

export function engineSourceRoot(): string {
  return join(app.getAppPath(), 'engine')
}

export function basePackagedEngineExecutable(): string {
  return join(
    process.resourcesPath,
    'engine-bin',
    'mel-engine',
    process.platform === 'win32' ? 'mel-engine.exe' : 'mel-engine',
  )
}

function sha256(path: string): string {
  return createHash('sha256').update(readFileSync(path)).digest('hex')
}

function safeBundleEntrypoint(root: string, entrypoint: string): string | undefined {
  const target = resolve(root, entrypoint)
  const relation = relative(resolve(root), target)
  if (relation === '..' || relation.startsWith(`..${sep}`) || isAbsolute(relation)) return undefined
  return target
}

function activeBundleEngineExecutable(): string | undefined {
  if (!app.isPackaged) return undefined
  const userData = app.getPath('userData')
  const pointerPath = join(userData, 'accelerator-bundles', 'active.json')
  if (!existsSync(pointerPath)) {
    activeEngineCache = undefined
    return undefined
  }
  const pointerMtime = Number(readFileSync(pointerPath).byteLength) + Number(process.env.MEL_ACTIVE_BUNDLE_REVISION ?? 0)
  if (activeEngineCache?.pointerMtime === pointerMtime) return activeEngineCache.executable
  try {
    const pointer = JSON.parse(readFileSync(pointerPath, 'utf8')) as ActiveBundlePointer
    if (pointer.schemaVersion !== 1 || !/^[a-z0-9][a-z0-9._-]{2,79}$/u.test(pointer.bundleId) || !/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/u.test(pointer.version)) throw new Error('Invalid active bundle pointer.')
    const root = join(userData, 'accelerator-bundles', 'installed', pointer.bundleId, pointer.version)
    const executable = safeBundleEntrypoint(root, pointer.entrypoint)
    if (!executable || !existsSync(executable)) throw new Error('Active bundle engine is missing.')
    if (!/^[0-9a-f]{64}$/iu.test(pointer.engineSha256) || sha256(executable) !== pointer.engineSha256.toLowerCase()) throw new Error('Active bundle engine failed integrity verification.')
    activeEngineCache = { pointerMtime, executable }
    return executable
  } catch {
    activeEngineCache = { pointerMtime, executable: undefined }
    return undefined
  }
}

export function packagedEngineExecutable(): string {
  return activeBundleEngineExecutable() ?? basePackagedEngineExecutable()
}

export function resetEngineProviderInventory(): void {
  providerInventoryPromise = undefined
  activeEngineCache = undefined
}

export async function engineReady(): Promise<boolean> {
  try {
    await access(
      app.isPackaged
        ? packagedEngineExecutable()
        : join(engineSourceRoot(), 'mel_engine', '__main__.py'),
    )
    return true
  } catch {
    return false
  }
}

export async function engineProviderInventory(refresh = false): Promise<EngineProviderInventory | undefined> {
  if (refresh) resetEngineProviderInventory()
  providerInventoryPromise ??= (async () => {
    if (!await engineReady()) return undefined
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 20_000)
    try {
      const result = await runEngine({ operation: 'providers' }, () => undefined, controller.signal)
      const available = result.available_providers
      const support = result.provider_support
      if (!Array.isArray(available) || !support || typeof support !== 'object') return undefined
      return result as unknown as EngineProviderInventory
    } catch {
      return undefined
    } finally {
      clearTimeout(timeout)
    }
  })()
  return providerInventoryPromise
}

function developmentPython(): string {
  if (process.env.MEL_PYTHON) return process.env.MEL_PYTHON
  return process.platform === 'win32' ? 'python' : 'python3'
}

export function runEngine(
  payload: Record<string, unknown>,
  onEvent: (event: EngineEvent) => void,
  signal: AbortSignal,
  environment: Record<string, string> = {},
): Promise<Record<string, unknown>> {
  return new Promise((resolvePromise, reject) => {
    const executable = app.isPackaged
      ? packagedEngineExecutable()
      : developmentPython()
    const args = app.isPackaged ? [] : ['-m', 'mel_engine']
    const cwd = app.isPackaged ? dirname(executable) : engineSourceRoot()
    const env = app.isPackaged
      ? { ...process.env, ...environment }
      : {
          ...process.env,
          ...environment,
          PYTHONPATH: engineSourceRoot(),
        }
    const child = spawn(executable, args, {
      cwd,
      env,
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
      shell: false,
    })
    let finalResult: Record<string, unknown> | undefined
    let settled = false
    const finish = (callback: () => void) => {
      if (settled) return
      settled = true
      callback()
    }
    const stdout = createInterface({ input: child.stdout })
    stdout.on('line', (line) => {
      try {
        const event = JSON.parse(line) as EngineEvent
        onEvent(event)
        if (event.type === 'result') finalResult = event.data ?? {}
        if (event.type === 'error') finish(() => reject(new Error(event.message ?? 'Engine error')))
      } catch {
        onEvent({ type: 'log', message: line })
      }
    })
    child.stderr.on('data', (chunk) => {
      onEvent({ type: 'log', message: String(chunk).trim() })
    })
    child.on('error', error => finish(() => reject(error)))
    child.on('exit', (code) => {
      if (code === 0) finish(() => resolvePromise(finalResult ?? {}))
      else finish(() => reject(new Error(`Engine exited with code ${code}`)))
    })
    signal.addEventListener('abort', () => {
      child.kill()
      finish(() => reject(new Error('Engine request aborted')))
    }, { once: true })
    child.stdin.write(`${JSON.stringify(payload)}\n`)
    child.stdin.end()
  })
}
