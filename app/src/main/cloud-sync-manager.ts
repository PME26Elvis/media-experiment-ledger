import { createHash } from 'node:crypto'
import {
  copyFileSync,
  existsSync,
  lstatSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  renameSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import { dirname, isAbsolute, join, relative, resolve, sep } from 'node:path'
import type {
  CloudSyncConflict,
  CloudSyncRequest,
  CloudSyncResult,
} from '../shared/integration-contracts'

interface ManifestEntry {
  path: string
  sha256: string
  sizeBytes: number
}

interface SyncSnapshot {
  schemaVersion: 1
  id: string
  parentId?: string
  createdAt: string
  files: ManifestEntry[]
}

interface ProjectSyncState {
  schemaVersion: 1
  remoteSnapshotId: string
  baseFiles: ManifestEntry[]
  updatedAt: string
}

const STATE_NAME = '.mel-sync-state.json'
const CONFLICT_DIRECTORY = '.mel-conflicts'
const EXCLUDED_TOP_LEVEL = new Set([STATE_NAME, CONFLICT_DIRECTORY, '.git'])

function sha256Bytes(bytes: Uint8Array): string {
  return createHash('sha256').update(bytes).digest('hex')
}

function sha256File(path: string): string {
  const hash = createHash('sha256')
  hash.update(readFileSync(path))
  return hash.digest('hex')
}

function atomicJson(path: string, value: unknown): void {
  mkdirSync(dirname(path), { recursive: true })
  const temporary = `${path}.tmp`
  writeFileSync(temporary, JSON.stringify(value, null, 2) + '\n', { encoding: 'utf8', mode: 0o600 })
  renameSync(temporary, path)
}

function normalizeRelative(path: string): string {
  const normalized = path.replaceAll('\\', '/')
  if (!normalized || normalized.startsWith('/') || normalized.includes('\0')) throw new Error('Invalid sync path.')
  const parts = normalized.split('/')
  if (parts.some(part => part === '' || part === '.' || part === '..')) throw new Error(`Unsafe sync path: ${path}`)
  return normalized
}

function pathInside(root: string, path: string): boolean {
  const rel = relative(resolve(root), resolve(path))
  return rel === '' || !rel.startsWith(`..${sep}`) && rel !== '..' && !isAbsolute(rel)
}

function assertSeparateRoots(projectRoot: string, syncRoot: string): void {
  const project = resolve(projectRoot)
  const sync = resolve(syncRoot)
  if (project === sync || pathInside(project, sync) || pathInside(sync, project)) {
    throw new Error('Project and sync roots must be separate, non-nested directories.')
  }
}

function scanTree(root: string): ManifestEntry[] {
  const entries: ManifestEntry[] = []
  const visit = (directory: string, prefix: string): void => {
    for (const item of readdirSync(directory, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      if (!prefix && EXCLUDED_TOP_LEVEL.has(item.name)) continue
      const fullPath = join(directory, item.name)
      const relativePath = normalizeRelative(prefix ? `${prefix}/${item.name}` : item.name)
      if (item.isSymbolicLink()) throw new Error(`Symbolic links are not synchronized: ${relativePath}`)
      if (item.isDirectory()) visit(fullPath, relativePath)
      else if (item.isFile()) {
        const stat = lstatSync(fullPath)
        entries.push({ path: relativePath, sha256: sha256File(fullPath), sizeBytes: stat.size })
      }
    }
  }
  visit(root, '')
  return entries.sort((a, b) => a.path.localeCompare(b.path))
}

function mapManifest(entries: ManifestEntry[]): Map<string, ManifestEntry> {
  return new Map(entries.map(entry => [entry.path, entry]))
}

function manifestsEqual(left: ManifestEntry[], right: ManifestEntry[]): boolean {
  if (left.length !== right.length) return false
  return left.every((entry, index) => {
    const other = right[index]
    return other?.path === entry.path && other.sha256 === entry.sha256 && other.sizeBytes === entry.sizeBytes
  })
}

function loadJson<T>(path: string): T | undefined {
  try { return JSON.parse(readFileSync(path, 'utf8')) as T } catch { return undefined }
}

function snapshotId(parentId: string | undefined, files: ManifestEntry[]): string {
  const canonical = JSON.stringify({ parentId: parentId ?? null, files })
  return sha256Bytes(Buffer.from(canonical, 'utf8')).slice(0, 32)
}

export class CloudSyncManager {
  sync(request: CloudSyncRequest): CloudSyncResult {
    const projectRoot = resolve(request.projectRoot)
    const syncRoot = resolve(request.syncRoot)
    assertSeparateRoots(projectRoot, syncRoot)
    if (!existsSync(projectRoot) || !lstatSync(projectRoot).isDirectory()) throw new Error('Project root is not a directory.')
    mkdirSync(syncRoot, { recursive: true })

    const metadataRoot = join(syncRoot, '.mel-sync')
    const blobsRoot = join(metadataRoot, 'blobs')
    const snapshotsRoot = join(metadataRoot, 'snapshots')
    const remoteHeadPath = join(metadataRoot, 'head.json')
    const projectStatePath = join(projectRoot, STATE_NAME)
    mkdirSync(blobsRoot, { recursive: true })
    mkdirSync(snapshotsRoot, { recursive: true })

    const localFiles = scanTree(projectRoot)
    const state = this.readState(projectStatePath)
    const remote = this.readRemoteHead(remoteHeadPath)

    if (!remote) {
      if (request.dryRun) return this.result('dry-run-initial', 'initialized', 0, 0, 0, [], projectStatePath, remoteHeadPath)
      const snapshot = this.uploadSnapshot(projectRoot, blobsRoot, snapshotsRoot, remoteHeadPath, undefined, localFiles)
      this.writeState(projectStatePath, snapshot)
      return this.result(snapshot.id, 'initialized', localFiles.length, 0, 0, [], projectStatePath, remoteHeadPath)
    }

    const baseFiles = state?.baseFiles ?? []
    const remoteChanged = state?.remoteSnapshotId !== remote.id
    const localChanged = !manifestsEqual(localFiles, baseFiles)

    if (!remoteChanged && !localChanged) {
      return this.result(remote.id, 'noop', 0, 0, 0, [], projectStatePath, remoteHeadPath)
    }

    if (!remoteChanged && localChanged) {
      if (request.dryRun) return this.result(remote.id, 'uploaded', localFiles.length, 0, 0, [], projectStatePath, remoteHeadPath)
      const snapshot = this.uploadSnapshot(projectRoot, blobsRoot, snapshotsRoot, remoteHeadPath, remote.id, localFiles)
      this.writeState(projectStatePath, snapshot)
      return this.result(snapshot.id, 'uploaded', localFiles.length, 0, 0, [], projectStatePath, remoteHeadPath)
    }

    if (remoteChanged && !localChanged) {
      if (request.dryRun) return this.result(remote.id, 'downloaded', 0, remote.files.length, 0, [], projectStatePath, remoteHeadPath)
      const applied = this.materialize(projectRoot, blobsRoot, localFiles, remote.files)
      this.writeState(projectStatePath, remote)
      return this.result(remote.id, 'downloaded', 0, applied.downloaded, applied.deleted, [], projectStatePath, remoteHeadPath)
    }

    const merge = this.merge(projectRoot, blobsRoot, baseFiles, localFiles, remote.files, Boolean(request.dryRun))
    if (request.dryRun) {
      return this.result(remote.id, 'merged', 0, merge.downloaded, merge.deleted, merge.conflicts, projectStatePath, remoteHeadPath)
    }
    const mergedFiles = scanTree(projectRoot)
    const snapshot = this.uploadSnapshot(projectRoot, blobsRoot, snapshotsRoot, remoteHeadPath, remote.id, mergedFiles)
    this.writeState(projectStatePath, snapshot)
    return this.result(snapshot.id, 'merged', mergedFiles.length, merge.downloaded, merge.deleted, merge.conflicts, projectStatePath, remoteHeadPath)
  }

  private merge(
    projectRoot: string,
    blobsRoot: string,
    baseFiles: ManifestEntry[],
    localFiles: ManifestEntry[],
    remoteFiles: ManifestEntry[],
    dryRun: boolean,
  ): { downloaded: number; deleted: number; conflicts: CloudSyncConflict[] } {
    const base = mapManifest(baseFiles)
    const local = mapManifest(localFiles)
    const remote = mapManifest(remoteFiles)
    const paths = [...new Set([...base.keys(), ...local.keys(), ...remote.keys()])].sort()
    const conflicts: CloudSyncConflict[] = []
    let downloaded = 0
    let deleted = 0
    const conflictStamp = new Date().toISOString().replaceAll(/[:.]/gu, '-')

    for (const path of paths) {
      const baseEntry = base.get(path)
      const localEntry = local.get(path)
      const remoteEntry = remote.get(path)
      const localChanged = localEntry?.sha256 !== baseEntry?.sha256
      const remoteChanged = remoteEntry?.sha256 !== baseEntry?.sha256
      if (!remoteChanged) continue
      if (localChanged && localEntry?.sha256 !== remoteEntry?.sha256) {
        let remoteCopyPath: string | undefined
        if (remoteEntry) {
          remoteCopyPath = join(projectRoot, CONFLICT_DIRECTORY, conflictStamp, `${path}.remote`)
          if (!dryRun) this.copyBlob(blobsRoot, remoteEntry, remoteCopyPath)
        }
        conflicts.push({
          path,
          baseSha256: baseEntry?.sha256,
          localSha256: localEntry?.sha256,
          remoteSha256: remoteEntry?.sha256,
          resolution: 'local-preserved',
          remoteCopyPath,
        })
        continue
      }
      if (dryRun) {
        if (remoteEntry) downloaded += 1
        else deleted += 1
        continue
      }
      const localPath = join(projectRoot, ...path.split('/'))
      if (!remoteEntry) {
        rmSync(localPath, { force: true })
        deleted += 1
      } else {
        this.copyBlob(blobsRoot, remoteEntry, localPath)
        downloaded += 1
      }
    }
    return { downloaded, deleted, conflicts }
  }

  private materialize(
    projectRoot: string,
    blobsRoot: string,
    localFiles: ManifestEntry[],
    remoteFiles: ManifestEntry[],
  ): { downloaded: number; deleted: number } {
    const local = mapManifest(localFiles)
    const remote = mapManifest(remoteFiles)
    let downloaded = 0
    let deleted = 0
    for (const [path] of local) {
      if (!remote.has(path)) {
        rmSync(join(projectRoot, ...path.split('/')), { force: true })
        deleted += 1
      }
    }
    for (const entry of remoteFiles) {
      if (local.get(entry.path)?.sha256 === entry.sha256) continue
      this.copyBlob(blobsRoot, entry, join(projectRoot, ...entry.path.split('/')))
      downloaded += 1
    }
    return { downloaded, deleted }
  }

  private copyBlob(blobsRoot: string, entry: ManifestEntry, destination: string): void {
    const blob = join(blobsRoot, entry.sha256.slice(0, 2), entry.sha256)
    if (!existsSync(blob) || sha256File(blob) !== entry.sha256) throw new Error(`Sync blob is missing or corrupt for ${entry.path}.`)
    mkdirSync(dirname(destination), { recursive: true })
    const temporary = `${destination}.mel-sync-tmp`
    copyFileSync(blob, temporary)
    renameSync(temporary, destination)
  }

  private uploadSnapshot(
    projectRoot: string,
    blobsRoot: string,
    snapshotsRoot: string,
    remoteHeadPath: string,
    parentId: string | undefined,
    files: ManifestEntry[],
  ): SyncSnapshot {
    for (const entry of files) {
      const source = join(projectRoot, ...entry.path.split('/'))
      const blob = join(blobsRoot, entry.sha256.slice(0, 2), entry.sha256)
      if (!existsSync(blob)) {
        mkdirSync(dirname(blob), { recursive: true })
        const temporary = `${blob}.tmp`
        copyFileSync(source, temporary)
        if (sha256File(temporary) !== entry.sha256) throw new Error(`Project file changed while synchronizing: ${entry.path}`)
        renameSync(temporary, blob)
      }
    }
    const snapshot: SyncSnapshot = {
      schemaVersion: 1,
      id: snapshotId(parentId, files),
      parentId,
      createdAt: new Date().toISOString(),
      files,
    }
    atomicJson(join(snapshotsRoot, `${snapshot.id}.json`), snapshot)
    atomicJson(remoteHeadPath, snapshot)
    return snapshot
  }

  private readRemoteHead(path: string): SyncSnapshot | undefined {
    const snapshot = loadJson<SyncSnapshot>(path)
    if (!snapshot) return undefined
    if (snapshot.schemaVersion !== 1 || !Array.isArray(snapshot.files) || typeof snapshot.id !== 'string') throw new Error('Remote sync head is invalid.')
    snapshot.files = snapshot.files.map(entry => ({ ...entry, path: normalizeRelative(entry.path) })).sort((a, b) => a.path.localeCompare(b.path))
    return snapshot
  }

  private readState(path: string): ProjectSyncState | undefined {
    const state = loadJson<ProjectSyncState>(path)
    if (!state || state.schemaVersion !== 1 || !Array.isArray(state.baseFiles)) return undefined
    state.baseFiles = state.baseFiles.map(entry => ({ ...entry, path: normalizeRelative(entry.path) })).sort((a, b) => a.path.localeCompare(b.path))
    return state
  }

  private writeState(path: string, snapshot: SyncSnapshot): void {
    atomicJson(path, {
      schemaVersion: 1,
      remoteSnapshotId: snapshot.id,
      baseFiles: snapshot.files,
      updatedAt: new Date().toISOString(),
    } satisfies ProjectSyncState)
  }

  private result(
    snapshotId: string,
    direction: CloudSyncResult['direction'],
    uploadedFiles: number,
    downloadedFiles: number,
    deletedFiles: number,
    conflicts: CloudSyncConflict[],
    projectStatePath: string,
    remoteHeadPath: string,
  ): CloudSyncResult {
    return { snapshotId, direction, uploadedFiles, downloadedFiles, deletedFiles, conflicts, projectStatePath, remoteHeadPath }
  }
}
