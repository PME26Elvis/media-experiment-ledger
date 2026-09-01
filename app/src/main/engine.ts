import { createHash, verify } from 'node:crypto'
import { app } from 'electron'
import { access } from 'node:fs/promises'
import { existsSync, lstatSync, readFileSync, statSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { spawn } from 'node:child_process'
import { createInterface } from 'node:readline'
import {
  acceleratorBundleManifestSchema,
  canonicalAcceleratorBundlePayload,
  compareVersions,
  safeBundlePath,
} from './accelerator-bundle-manager'
import type { AcceleratorBundleManifest } from '../shared/accelerator-bundle-contracts'

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
  profile: string
  entrypoint: string
  engineSha256: string
}

let providerInventoryPromise: Promise<EngineProviderInventory | undefined> | undefined
let activeEngineCache: { pointerFingerprint: string; executable?: string } | undefined

export function engineSourceRoot(): string {
  return join(app.getAppPath(), 'engine')
}

export function basePackagedEngineExecutable(): string {
  return join(process.resourcesPath, 'engine-bin', 'mel-engine', process.platform === 'win32' ? 'mel-engine.exe' : 'mel-engine')
}

function sha256(path: string): string {
  return createHash('sha256').update(readFileSync(path)).digest('hex')
}

function trustKeyPath(userData: string): string | undefined {
  const candidates = [
    join(userData, 'accelerator-bundle-public-key.pem'),
    join(process.resourcesPath, 'accelerator-bundle-public-key.pem'),
    join(userData, 'update-public-key.pem'),
    join(process.resourcesPath, 'update-public-key.pem'),
  ]
  return candidates.find(path => existsSync(path) && statSync(path).isFile())
}

function verifyManifestIdentity(manifest: AcceleratorBundleManifest, pointer: ActiveBundlePointer): void {
  if (manifest.bundleId !== pointer.bundleId || manifest.version !== pointer.version || manifest.profile !== pointer.profile) throw new Error('Active bundle pointer does not match the signed manifest identity.')
  if (manifest.engine.entrypoint !== pointer.entrypoint || manifest.engine.sha256.toLowerCase() !== pointer.engineSha256.toLowerCase()) throw new Error('Active bundle pointer does not match the signed engine identity.')
  if (manifest.platform !== process.platform || manifest.arch !== process.arch) throw new Error('Active accelerator bundle does not match this host.')
  if (compareVersions(app.getVersion(), manifest.appVersion.minimum) < 0) throw new Error('Active accelerator bundle requires a newer Studio version.')
  if (manifest.appVersion.maximum && compareVersions(app.getVersion(), manifest.appVersion.maximum) > 0) throw new Error('Active accelerator bundle is not compatible with this Studio version.')
}

function verifySignedManifest(manifest: AcceleratorBundleManifest, userData: string): void {
  const payload = canonicalAcceleratorBundlePayload(manifest)
  if (manifest.signedPayload !== payload) throw new Error('Active accelerator bundle signed payload is inconsistent.')
  const key = trustKeyPath(userData)
  if (!key) throw new Error('No accelerator bundle trust key is installed.')
  if (!verify(null, Buffer.from(payload, 'utf8'), readFileSync(key), Buffer.from(manifest.signature, 'base64'))) throw new Error('Active accelerator bundle signature is invalid.')
}

function verifyBundleFiles(manifest: AcceleratorBundleManifest, root: string): string {
  for (const file of manifest.files) {
    const path = safeBundlePath(root, file.path)
    if (!existsSync(path)) throw new Error(`Active accelerator bundle file is missing: ${file.path}`)
    const details = lstatSync(path)
    if (details.isSymbolicLink() || !details.isFile()) throw new Error(`Active accelerator bundle entry is not a regular file: ${file.path}`)
    if (details.size !== file.sizeBytes || sha256(path) !== file.sha256.toLowerCase()) throw new Error(`Active accelerator bundle integrity failed: ${file.path}`)
  }
  const executable = safeBundlePath(root, manifest.engine.entrypoint)
  if (sha256(executable) !== manifest.engine.sha256.toLowerCase()) throw new Error('Active accelerator engine entrypoint integrity failed.')
  return executable
}

function activeBundleEngineExecutable(): string | undefined {
  if (!app.isPackaged) return undefined
  const userData = app.getPath('userData')
  const pointerPath = join(userData, 'accelerator-bundles', 'active.json')
  if (!existsSync(pointerPath)) {
    activeEngineCache = undefined
    return undefined
  }
  const pointerBytes = readFileSync(pointerPath)
  const pointerFingerprint = createHash('sha256').update(pointerBytes).digest('hex')
  if (activeEngineCache?.pointerFingerprint === pointerFingerprint) return activeEngineCache.executable
  try {
    const pointer = JSON.parse(pointerBytes.toString('utf8')) as ActiveBundlePointer
    if (pointer.schemaVersion !== 1 || !/^[a-z0-9][a-z0-9._-]{2,79}$/u.test(pointer.bundleId) || !/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/u.test(pointer.version)) throw new Error('Invalid active bundle pointer.')
    const root = join(userData, 'accelerator-bundles', 'installed', pointer.bundleId, pointer.version)
    const manifestPath = join(root, 'accelerator-bundle-manifest.json')
    if (!existsSync(manifestPath)) throw new Error('Active bundle manifest is missing.')
    const manifest = acceleratorBundleManifestSchema.parse(JSON.parse(readFileSync(manifestPath, 'utf8'))) as AcceleratorBundleManifest
    verifyManifestIdentity(manifest, pointer)
    verifySignedManifest(manifest, userData)
    const executable = verifyBundleFiles(manifest, root)
    activeEngineCache = { pointerFingerprint, executable }
    return executable
  } catch {
    activeEngineCache = { pointerFingerprint, executable: undefined }
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
    await access(app.isPackaged ? packagedEngineExecutable() : join(engineSourceRoot(), 'mel_engine', '__main__.py'))
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
    const executable = app.isPackaged ? packagedEngineExecutable() : developmentPython()
    const args = app.isPackaged ? [] : ['-m', 'mel_engine']
    const cwd = app.isPackaged ? dirname(executable) : engineSourceRoot()
    const env = app.isPackaged ? { ...process.env, ...environment } : { ...process.env, ...environment, PYTHONPATH: engineSourceRoot() }
    const child = spawn(executable, args, { cwd, env, stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true, shell: false })
    let finalResult: Record<string, unknown> | undefined
    let settled = false
    const finish = (callback: () => void) => {
      if (settled) return
      settled = true
      callback()
    }
    const stdout = createInterface({ input: child.stdout })
    stdout.on('line', line => {
      try {
        const event = JSON.parse(line) as EngineEvent
        onEvent(event)
        if (event.type === 'result') finalResult = event.data ?? {}
        if (event.type === 'error') finish(() => reject(new Error(event.message ?? 'Engine error')))
      } catch { onEvent({ type: 'log', message: line }) }
    })
    child.stderr.on('data', chunk => onEvent({ type: 'log', message: String(chunk).trim() }))
    child.on('error', error => finish(() => reject(error)))
    child.on('exit', code => {
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
