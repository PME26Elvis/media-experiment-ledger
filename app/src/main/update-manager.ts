import { createHash, verify } from 'node:crypto'
import { app, shell } from 'electron'
import { autoUpdater } from 'electron-updater'
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  statSync,
  writeFileSync,
} from 'node:fs'
import { basename, dirname, join, resolve } from 'node:path'
import { z } from 'zod'
import type { OfflineUpdateManifest, UpdateStatus } from '../shared/contracts'
import type { JobManager } from './job-manager'
import type { RecoveryManager } from './recovery-manager'

const releaseUrl = 'https://github.com/PME26Elvis/media-experiment-ledger/releases'

const manifestSchema = z.object({
  schemaVersion: z.literal(1),
  version: z.string().regex(/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/u),
  channel: z.enum(['alpha', 'beta', 'stable']),
  platform: z.enum(['aix', 'android', 'darwin', 'freebsd', 'haiku', 'linux', 'openbsd', 'sunos', 'win32', 'cygwin', 'netbsd']),
  arch: z.string().min(1).max(32),
  packageFile: z.string().min(1).max(255).refine(value => basename(value) === value, 'packageFile must be a filename'),
  packageSizeBytes: z.number().int().positive(),
  packageSha256: z.string().regex(/^[0-9a-f]{64}$/iu),
  signature: z.string().max(8192).optional(),
  signedPayload: z.string().max(65536).optional(),
})

function sha256(path: string): string {
  const digest = createHash('sha256')
  digest.update(readFileSync(path))
  return digest.digest('hex')
}

function safeVersion(value: string): string {
  if (!/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/u.test(value)) throw new Error('Invalid update version.')
  return value
}

function publicKeyPath(userDataPath: string): string | undefined {
  const candidates = [
    join(userDataPath, 'update-public-key.pem'),
    join(process.resourcesPath, 'update-public-key.pem'),
  ]
  return candidates.find(path => existsSync(path))
}

function verifyOfflineSignature(manifest: OfflineUpdateManifest, userDataPath: string): { verified: boolean; warning?: string } {
  const keyPath = publicKeyPath(userDataPath)
  if (!manifest.signature || !manifest.signedPayload || !keyPath) {
    if (manifest.channel === 'stable') {
      throw new Error('Stable offline updates require an Ed25519 signature and installed update public key.')
    }
    return { verified: false, warning: 'Prerelease offline package passed SHA-256 verification but has no trusted signature.' }
  }
  const expectedPayload = JSON.stringify({
    schemaVersion: manifest.schemaVersion,
    version: manifest.version,
    channel: manifest.channel,
    platform: manifest.platform,
    arch: manifest.arch,
    packageFile: manifest.packageFile,
    packageSizeBytes: manifest.packageSizeBytes,
    packageSha256: manifest.packageSha256,
  })
  if (manifest.signedPayload !== expectedPayload) throw new Error('Offline update signed payload does not match manifest fields.')
  const valid = verify(
    null,
    Buffer.from(manifest.signedPayload, 'utf8'),
    readFileSync(keyPath),
    Buffer.from(manifest.signature, 'base64'),
  )
  if (!valid) throw new Error('Offline update Ed25519 signature verification failed.')
  return { verified: true }
}

export class UpdateManager {
  private current: UpdateStatus
  private stagedPackagePath: string | undefined

  constructor(
    private readonly userDataPath: string,
    private readonly recovery: RecoveryManager,
    private readonly jobs: JobManager,
    channel: 'alpha' | 'beta' | 'stable',
  ) {
    this.current = {
      state: 'idle',
      currentVersion: app.getVersion(),
      channel,
      releaseUrl,
    }
    autoUpdater.autoDownload = false
    autoUpdater.autoInstallOnAppQuit = false
    autoUpdater.allowPrerelease = channel !== 'stable'
    autoUpdater.channel = channel
    autoUpdater.on('checking-for-update', () => this.patch({ state: 'checking', error: undefined }))
    autoUpdater.on('update-available', info => this.patch({ state: 'available', availableVersion: info.version }))
    autoUpdater.on('update-not-available', () => this.patch({ state: 'current', availableVersion: undefined }))
    autoUpdater.on('download-progress', progress => this.patch({ state: 'downloading', progress: progress.percent }))
    autoUpdater.on('update-downloaded', info => this.patch({ state: 'downloaded', availableVersion: info.version, progress: 100 }))
    autoUpdater.on('error', error => this.patch({ state: 'error', error: error.message }))
  }

  setChannel(channel: 'alpha' | 'beta' | 'stable'): UpdateStatus {
    autoUpdater.allowPrerelease = channel !== 'stable'
    autoUpdater.channel = channel
    return this.patch({ channel, state: 'idle', availableVersion: undefined, error: undefined })
  }

  status(): UpdateStatus {
    return { ...this.current }
  }

  async check(): Promise<UpdateStatus> {
    if (process.platform === 'linux') {
      return this.patch({
        state: 'manual',
        releaseUrl,
        warning: 'Linux updates use signed release packages and are installed manually.',
        checkedAt: new Date().toISOString(),
      })
    }
    if (!app.isPackaged) {
      return this.patch({
        state: 'manual',
        releaseUrl,
        warning: 'Automatic update checks are disabled in development builds.',
        checkedAt: new Date().toISOString(),
      })
    }
    try {
      this.patch({ state: 'checking', error: undefined, warning: undefined })
      const result = await autoUpdater.checkForUpdates()
      return this.patch({
        checkedAt: new Date().toISOString(),
        state: result?.updateInfo.version && result.updateInfo.version !== app.getVersion() ? 'available' : 'current',
        availableVersion: result?.updateInfo.version,
      })
    } catch (error) {
      return this.patch({ state: 'error', error: error instanceof Error ? error.message : String(error), checkedAt: new Date().toISOString() })
    }
  }

  async download(): Promise<UpdateStatus> {
    if (this.current.state !== 'available') throw new Error('No online update is ready to download.')
    if (this.jobs.activeCount() > 0) throw new Error('Pause or finish active jobs before downloading an application update.')
    this.patch({ state: 'downloading', progress: 0 })
    await autoUpdater.downloadUpdate()
    return this.status()
  }

  install(): boolean {
    if (this.current.state !== 'downloaded') throw new Error('No verified online update has been downloaded.')
    if (this.jobs.activeCount() > 0) throw new Error('Pause or finish active jobs before installing an application update.')
    this.recovery.create(`Automatic backup before online update to ${this.current.availableVersion ?? 'unknown'}`)
    autoUpdater.quitAndInstall(false, true)
    return true
  }

  importOffline(manifestPath: string, packagePath: string): UpdateStatus {
    const parsed = manifestSchema.parse(JSON.parse(readFileSync(resolve(manifestPath), 'utf8'))) as OfflineUpdateManifest
    const packageResolved = resolve(packagePath)
    if (!existsSync(packageResolved) || !statSync(packageResolved).isFile()) throw new Error('Offline update package does not exist.')
    if (basename(packageResolved) !== parsed.packageFile) throw new Error('Offline package filename does not match its manifest.')
    if (parsed.platform !== process.platform || parsed.arch !== process.arch) {
      throw new Error(`Offline update targets ${parsed.platform}/${parsed.arch}, but this system is ${process.platform}/${process.arch}.`)
    }
    if (statSync(packageResolved).size !== parsed.packageSizeBytes) throw new Error('Offline update package size mismatch.')
    if (sha256(packageResolved) !== parsed.packageSha256.toLowerCase()) throw new Error('Offline update package SHA-256 mismatch.')
    const signature = verifyOfflineSignature(parsed, this.userDataPath)
    const root = join(this.userDataPath, 'offline-updates', safeVersion(parsed.version))
    mkdirSync(root, { recursive: true })
    const stagedPackage = join(root, parsed.packageFile)
    const stagedManifest = join(root, 'offline-update-manifest.json')
    copyFileSync(packageResolved, stagedPackage)
    copyFileSync(resolve(manifestPath), stagedManifest)
    writeFileSync(join(root, 'verification.json'), JSON.stringify({
      schemaVersion: 1,
      verifiedAt: new Date().toISOString(),
      sha256Verified: true,
      signatureVerified: signature.verified,
      packagePath: stagedPackage,
    }, null, 2), 'utf8')
    this.stagedPackagePath = stagedPackage
    return this.patch({
      state: 'offline-staged',
      availableVersion: parsed.version,
      packagePath: stagedPackage,
      warning: signature.warning,
      error: undefined,
    })
  }

  async openOffline(): Promise<boolean> {
    if (!this.stagedPackagePath || !existsSync(this.stagedPackagePath)) throw new Error('No verified offline update is staged.')
    if (this.jobs.activeCount() > 0) throw new Error('Pause or finish active jobs before opening an offline installer.')
    this.recovery.create(`Automatic backup before offline update ${this.current.availableVersion ?? ''}`.trim())
    const error = await shell.openPath(this.stagedPackagePath)
    if (error) throw new Error(error)
    return true
  }

  private patch(patch: Partial<UpdateStatus>): UpdateStatus {
    this.current = { ...this.current, ...patch }
    return this.status()
  }
}
