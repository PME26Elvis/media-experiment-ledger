import { createHash, randomUUID } from 'node:crypto'
import {
  copyFileSync,
  cpSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  renameSync,
  rmSync,
  statSync,
  writeFileSync,
} from 'node:fs'
import { basename, dirname, join, relative, resolve, sep } from 'node:path'
import type { StudioDatabase } from './database'

export interface RecoveryBackupSummary {
  id: string
  reason: string
  appVersion: string
  createdAt: string
  fileCount: number
  totalBytes: number
  manifestPath: string
  verified: boolean
}

interface RecoveryFile {
  path: string
  sizeBytes: number
  sha256: string
}

interface RecoveryManifest {
  schemaVersion: 1
  id: string
  reason: string
  appVersion: string
  createdAt: string
  files: RecoveryFile[]
}

const STATE_PATHS = [
  'studio.sqlite',
  'reports',
  'secrets',
  'sample-corpora/catalog.json',
  'maintenance.json',
]

function sha256(path: string): string {
  const digest = createHash('sha256')
  const content = readFileSync(path)
  digest.update(content)
  return digest.digest('hex')
}

function atomicJson(path: string, value: unknown): void {
  mkdirSync(dirname(path), { recursive: true })
  const temporary = `${path}.${randomUUID()}.tmp`
  writeFileSync(temporary, JSON.stringify(value, null, 2), 'utf8')
  renameSync(temporary, path)
}

function walk(root: string): string[] {
  if (!existsSync(root)) return []
  if (statSync(root).isFile()) return [root]
  const files: string[] = []
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    const path = join(root, entry.name)
    if (entry.isDirectory()) files.push(...walk(path))
    else if (entry.isFile()) files.push(path)
  }
  return files.sort((a, b) => a.localeCompare(b))
}

function safeBackupId(value: string): string {
  if (!/^[A-Za-z0-9._-]{1,160}$/u.test(value)) throw new Error('Invalid recovery backup ID.')
  return value
}

function manifestFrom(path: string): RecoveryManifest {
  const value = JSON.parse(readFileSync(path, 'utf8')) as RecoveryManifest
  if (value.schemaVersion !== 1 || !value.id || !Array.isArray(value.files)) {
    throw new Error(`Unsupported recovery manifest: ${path}`)
  }
  return value
}

function verifyManifest(root: string, manifest: RecoveryManifest): boolean {
  for (const file of manifest.files) {
    if (file.path.includes('..') || file.path.startsWith('/') || file.path.startsWith('\\')) return false
    const path = resolve(root, file.path)
    if (!path.startsWith(`${resolve(root)}${sep}`) || !existsSync(path) || !statSync(path).isFile()) return false
    if (statSync(path).size !== file.sizeBytes || sha256(path) !== file.sha256) return false
  }
  return true
}

export function applyPendingRecovery(userDataPath: string): { applied: boolean; backupId?: string } {
  const planPath = join(userDataPath, 'pending-recovery.json')
  if (!existsSync(planPath)) return { applied: false }
  const plan = JSON.parse(readFileSync(planPath, 'utf8')) as { backupId?: string }
  const backupId = safeBackupId(String(plan.backupId ?? ''))
  const backupRoot = join(userDataPath, 'recovery-backups', backupId)
  const manifest = manifestFrom(join(backupRoot, 'manifest.json'))
  if (!verifyManifest(backupRoot, manifest)) {
    renameSync(planPath, `${planPath}.invalid-${Date.now()}`)
    throw new Error(`Recovery backup ${backupId} failed SHA-256 verification.`)
  }

  const staging = join(userDataPath, `.recovery-staging-${randomUUID()}`)
  mkdirSync(staging, { recursive: true })
  try {
    for (const file of manifest.files) {
      const source = join(backupRoot, file.path)
      const destination = join(staging, file.path)
      mkdirSync(dirname(destination), { recursive: true })
      copyFileSync(source, destination)
    }
    for (const relativePath of STATE_PATHS) {
      const current = join(userDataPath, relativePath)
      const staged = join(staging, relativePath)
      rmSync(current, { recursive: true, force: true })
      if (existsSync(staged)) {
        mkdirSync(dirname(current), { recursive: true })
        cpSync(staged, current, { recursive: true, force: true })
      }
    }
    rmSync(planPath, { force: true })
    atomicJson(join(userDataPath, 'last-recovery.json'), {
      schemaVersion: 1,
      backupId,
      appliedAt: new Date().toISOString(),
    })
    return { applied: true, backupId }
  } finally {
    rmSync(staging, { recursive: true, force: true })
  }
}

export class RecoveryManager {
  private readonly backupsRoot: string

  constructor(
    private readonly userDataPath: string,
    private readonly database: StudioDatabase,
    private readonly appVersion: string,
  ) {
    this.backupsRoot = join(userDataPath, 'recovery-backups')
    mkdirSync(this.backupsRoot, { recursive: true })
  }

  create(reason: string): RecoveryBackupSummary {
    this.database.checkpoint()
    const createdAt = new Date().toISOString()
    const id = `${createdAt.replace(/[:.]/gu, '-')}-${randomUUID().slice(0, 8)}`
    const root = join(this.backupsRoot, id)
    mkdirSync(root, { recursive: true })

    for (const relativePath of STATE_PATHS) {
      const source = join(this.userDataPath, relativePath)
      if (!existsSync(source)) continue
      const destination = join(root, relativePath)
      mkdirSync(dirname(destination), { recursive: true })
      cpSync(source, destination, { recursive: true, force: true })
    }

    const files = walk(root)
      .filter(path => basename(path) !== 'manifest.json')
      .map(path => ({
        path: relative(root, path).split(sep).join('/'),
        sizeBytes: statSync(path).size,
        sha256: sha256(path),
      }))
    const manifest: RecoveryManifest = {
      schemaVersion: 1,
      id,
      reason: reason.slice(0, 300),
      appVersion: this.appVersion,
      createdAt,
      files,
    }
    atomicJson(join(root, 'manifest.json'), manifest)
    return this.summary(root, manifest)
  }

  list(): RecoveryBackupSummary[] {
    return readdirSync(this.backupsRoot, { withFileTypes: true })
      .filter(entry => entry.isDirectory())
      .map(entry => join(this.backupsRoot, entry.name))
      .flatMap(root => {
        try {
          const manifest = manifestFrom(join(root, 'manifest.json'))
          return [this.summary(root, manifest)]
        } catch {
          return []
        }
      })
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
  }

  scheduleRestore(id: string): { backupId: string; requiresRestart: true } {
    const backupId = safeBackupId(id)
    const root = join(this.backupsRoot, backupId)
    const manifest = manifestFrom(join(root, 'manifest.json'))
    if (!verifyManifest(root, manifest)) throw new Error(`Recovery backup ${backupId} failed verification.`)
    this.create(`Automatic pre-restore backup before restoring ${backupId}`)
    atomicJson(join(this.userDataPath, 'pending-recovery.json'), {
      schemaVersion: 1,
      backupId,
      scheduledAt: new Date().toISOString(),
    })
    return { backupId, requiresRestart: true }
  }

  remove(id: string): boolean {
    const root = join(this.backupsRoot, safeBackupId(id))
    if (!existsSync(root)) return false
    rmSync(root, { recursive: true, force: true })
    return true
  }

  private summary(root: string, manifest: RecoveryManifest): RecoveryBackupSummary {
    return {
      id: manifest.id,
      reason: manifest.reason,
      appVersion: manifest.appVersion,
      createdAt: manifest.createdAt,
      fileCount: manifest.files.length,
      totalBytes: manifest.files.reduce((sum, file) => sum + file.sizeBytes, 0),
      manifestPath: join(root, 'manifest.json'),
      verified: verifyManifest(root, manifest),
    }
  }
}
