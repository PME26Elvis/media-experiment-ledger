import { createHash, randomUUID, verify } from 'node:crypto'
import {
  chmodSync,
  copyFileSync,
  existsSync,
  lstatSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  renameSync,
  rmSync,
  statSync,
  writeFileSync,
} from 'node:fs'
import { execFileSync, spawnSync } from 'node:child_process'
import { basename, dirname, isAbsolute, join, normalize, relative, resolve, sep } from 'node:path'
import { release } from 'node:os'
import { z } from 'zod'
import type {
  AcceleratorBundleManifest,
  AcceleratorBundleProfile,
  AcceleratorBundleRecord,
  AcceleratorBundleSnapshot,
  AcceleratorBundleVerification,
} from '../shared/accelerator-bundle-contracts'

const semverPattern = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/u
const shaPattern = /^[0-9a-f]{64}$/iu
const idPattern = /^[a-z0-9][a-z0-9._-]{2,79}$/u
const platformSchema = z.enum(['aix', 'android', 'darwin', 'freebsd', 'haiku', 'linux', 'openbsd', 'sunos', 'win32', 'cygwin', 'netbsd'])
const relativePathSchema = z.string().min(1).max(1024).refine(value => {
  const normalized = normalize(value)
  return !isAbsolute(value) && normalized !== '..' && !normalized.startsWith(`..${sep}`) && basename(normalized) !== '.'
}, 'Path must stay inside the bundle root.')

export const acceleratorBundleManifestSchema = z.object({
  schemaVersion: z.literal(1),
  bundleId: z.string().regex(idPattern),
  version: z.string().regex(semverPattern),
  profile: z.enum(['directml', 'cuda', 'coreml']),
  platform: platformSchema,
  arch: z.string().min(1).max(32),
  appVersion: z.object({ minimum: z.string().regex(semverPattern), maximum: z.string().regex(semverPattern).optional() }),
  engine: z.object({
    entrypoint: relativePathSchema,
    sha256: z.string().regex(shaPattern),
    onnxRuntimeVersion: z.string().min(1).max(80),
    requiredProviders: z.array(z.string().min(1).max(120)).min(1).max(16),
    distributions: z.record(z.string(), z.string()),
  }),
  runtimeRequirements: z.object({
    minimumOsVersion: z.string().max(80).optional(),
    minimumNvidiaDriver: z.string().max(80).optional(),
    cudaMajor: z.number().int().positive().max(99).optional(),
    cudnnMajor: z.number().int().positive().max(99).optional(),
  }),
  files: z.array(z.object({
    path: relativePathSchema,
    sizeBytes: z.number().int().nonnegative(),
    sha256: z.string().regex(shaPattern),
    kind: z.enum(['engine', 'native', 'metadata', 'license', 'sbom']),
  })).min(4).max(100_000),
  sbomFile: relativePathSchema,
  noticesFile: relativePathSchema,
  nativeInventoryFile: relativePathSchema,
  signedPayload: z.string().min(1).max(2_000_000),
  signature: z.string().min(1).max(16_384),
}).superRefine((manifest, context) => {
  const paths = new Set<string>()
  for (const [index, file] of manifest.files.entries()) {
    if (paths.has(file.path)) context.addIssue({ code: 'custom', path: ['files', index, 'path'], message: 'Duplicate bundle file path.' })
    paths.add(file.path)
  }
  for (const required of [manifest.engine.entrypoint, manifest.sbomFile, manifest.noticesFile, manifest.nativeInventoryFile]) {
    if (!paths.has(required)) context.addIssue({ code: 'custom', message: `Required bundle file is absent from inventory: ${required}` })
  }
})

interface ActivePointer {
  schemaVersion: 1
  bundleId: string
  version: string
  profile: AcceleratorBundleProfile
  entrypoint: string
  engineSha256: string
  activatedAt: string
  history: Array<{ bundleId: string; version: string; profile: AcceleratorBundleProfile }>
}

interface BundleJobGate {
  activeCount(): number
  resetEngineRuntime(): void
}

interface ParsedVersion {
  core: number[]
  prerelease: string[]
}

function sha256File(path: string): string {
  return createHash('sha256').update(readFileSync(path)).digest('hex')
}

function sha256Text(value: string): string {
  return createHash('sha256').update(value, 'utf8').digest('hex')
}

function parseVersion(value: string): ParsedVersion {
  const match = value.trim().match(/^(\d+(?:\.\d+)*)(?:-([0-9A-Za-z.-]+))?/u)
  if (!match) return { core: [0], prerelease: [] }
  return {
    core: match[1].split('.').map(part => Number(part)),
    prerelease: match[2]?.split('.') ?? [],
  }
}

function compareIdentifier(left: string, right: string): number {
  const leftNumeric = /^\d+$/u.test(left)
  const rightNumeric = /^\d+$/u.test(right)
  if (leftNumeric && rightNumeric) return Number(left) - Number(right)
  if (leftNumeric !== rightNumeric) return leftNumeric ? -1 : 1
  return left.localeCompare(right)
}

export function compareVersions(left: string, right: string): number {
  const a = parseVersion(left)
  const b = parseVersion(right)
  for (let index = 0; index < Math.max(a.core.length, b.core.length); index += 1) {
    const difference = (a.core[index] ?? 0) - (b.core[index] ?? 0)
    if (difference !== 0) return difference
  }
  if (a.prerelease.length === 0 && b.prerelease.length === 0) return 0
  if (a.prerelease.length === 0) return 1
  if (b.prerelease.length === 0) return -1
  for (let index = 0; index < Math.max(a.prerelease.length, b.prerelease.length); index += 1) {
    const leftIdentifier = a.prerelease[index]
    const rightIdentifier = b.prerelease[index]
    if (leftIdentifier === undefined) return -1
    if (rightIdentifier === undefined) return 1
    const difference = compareIdentifier(leftIdentifier, rightIdentifier)
    if (difference !== 0) return difference
  }
  return 0
}

function orderedFiles(manifest: AcceleratorBundleManifest) {
  return [...manifest.files].sort((left, right) => left.path.localeCompare(right.path)).map(file => ({
    path: file.path,
    sizeBytes: file.sizeBytes,
    sha256: file.sha256.toLowerCase(),
    kind: file.kind,
  }))
}

export function canonicalAcceleratorBundlePayload(manifest: AcceleratorBundleManifest): string {
  return JSON.stringify({
    schemaVersion: manifest.schemaVersion,
    bundleId: manifest.bundleId,
    version: manifest.version,
    profile: manifest.profile,
    platform: manifest.platform,
    arch: manifest.arch,
    appVersion: manifest.appVersion,
    engine: {
      entrypoint: manifest.engine.entrypoint,
      sha256: manifest.engine.sha256.toLowerCase(),
      onnxRuntimeVersion: manifest.engine.onnxRuntimeVersion,
      requiredProviders: [...manifest.engine.requiredProviders].sort(),
      distributions: Object.fromEntries(Object.entries(manifest.engine.distributions).sort(([left], [right]) => left.localeCompare(right))),
    },
    runtimeRequirements: manifest.runtimeRequirements,
    files: orderedFiles(manifest),
    sbomFile: manifest.sbomFile,
    noticesFile: manifest.noticesFile,
    nativeInventoryFile: manifest.nativeInventoryFile,
  })
}

function safeInside(root: string, relativePath: string): string {
  const target = resolve(root, relativePath)
  const relation = relative(resolve(root), target)
  if (relation === '..' || relation.startsWith(`..${sep}`) || isAbsolute(relation)) throw new Error(`Bundle path escapes its root: ${relativePath}`)
  return target
}

function providerFor(profile: AcceleratorBundleProfile): string {
  if (profile === 'directml') return 'DmlExecutionProvider'
  if (profile === 'cuda') return 'CUDAExecutionProvider'
  return 'CoreMLExecutionProvider'
}

function profileSupportsHost(profile: AcceleratorBundleProfile, platform: NodeJS.Platform): boolean {
  if (profile === 'directml') return platform === 'win32'
  if (profile === 'coreml') return platform === 'darwin'
  return platform === 'linux' || platform === 'win32'
}

function parseMajor(value?: string): number | undefined {
  if (!value) return undefined
  const match = value.match(/(?:^|[^0-9])(\d{1,2})(?:\.|$)/u)
  return match ? Number(match[1]) : undefined
}

function readJson<T>(path: string): T | undefined {
  try { return JSON.parse(readFileSync(path, 'utf8')) as T } catch { return undefined }
}

export class AcceleratorBundleManager {
  private readonly root: string
  private readonly installedRoot: string
  private readonly stagingRoot: string
  private readonly quarantineRoot: string
  private readonly activePath: string

  constructor(
    private readonly userDataPath: string,
    private readonly resourcesPath: string,
    private readonly appVersion: string,
    private readonly jobs: BundleJobGate,
  ) {
    this.root = join(userDataPath, 'accelerator-bundles')
    this.installedRoot = join(this.root, 'installed')
    this.stagingRoot = join(this.root, 'staging')
    this.quarantineRoot = join(this.root, 'quarantine')
    this.activePath = join(this.root, 'active.json')
    for (const path of [this.root, this.installedRoot, this.stagingRoot, this.quarantineRoot]) mkdirSync(path, { recursive: true })
    this.removeAbandonedStaging()
  }

  snapshot(): AcceleratorBundleSnapshot {
    const active = this.activePointer()
    const installed = this.scanRecords(this.installedRoot, 'installed').map(record => active && record.bundleId === active.bundleId && record.version === active.version
      ? { ...record, state: 'active' as const, activatedAt: active.activatedAt }
      : record)
    const quarantined = this.scanRecords(this.quarantineRoot, 'quarantined')
    const trustKeyPath = this.trustKeyPath()
    const warnings: string[] = []
    if (!trustKeyPath) warnings.push('No accelerator bundle trust key is installed. Bundle installation is fail-closed.')
    if (!active) warnings.push('The universal CPU engine is active.')
    return {
      schemaVersion: 1,
      capturedAt: new Date().toISOString(),
      trustKeyPath,
      active: active ? { bundleId: active.bundleId, version: active.version, profile: active.profile, activatedAt: active.activatedAt } : undefined,
      installed,
      quarantined,
      host: {
        platform: process.platform,
        arch: process.arch,
        appVersion: this.appVersion,
        osVersion: release(),
        nvidiaDriver: this.nvidiaDriver(),
      },
      warnings,
    }
  }

  install(manifestPath: string): AcceleratorBundleRecord {
    this.assertMaintenanceWindow()
    const resolvedManifest = resolve(manifestPath)
    if (!existsSync(resolvedManifest) || !statSync(resolvedManifest).isFile()) throw new Error('Accelerator bundle manifest does not exist.')
    const sourceRoot = dirname(resolvedManifest)
    const rawManifest = readFileSync(resolvedManifest, 'utf8')
    const manifest = acceleratorBundleManifestSchema.parse(JSON.parse(rawManifest)) as AcceleratorBundleManifest
    this.validateCompatibility(manifest)
    this.verifyManifestSignature(manifest)
    const stage = join(this.stagingRoot, `${manifest.bundleId}-${manifest.version}-${randomUUID()}`)
    mkdirSync(stage, { recursive: true })
    writeFileSync(join(stage, 'accelerator-bundle-manifest.json'), rawManifest, 'utf8')
    try {
      const verification = this.verifyAndCopyFiles(manifest, sourceRoot, stage, rawManifest)
      const inventory = this.runProviderInventory(manifest, stage)
      verification.providerSelfTestPassed = true
      verification.providerInventory = inventory
      writeFileSync(join(stage, 'verification.json'), `${JSON.stringify(verification, null, 2)}\n`, 'utf8')
      const target = join(this.installedRoot, manifest.bundleId, manifest.version)
      mkdirSync(dirname(target), { recursive: true })
      if (existsSync(target)) this.moveToQuarantine(target, manifest.bundleId, manifest.version, 'Replaced by a newly verified installation.')
      renameSync(stage, target)
      return this.recordFromPath(target, 'installed')
    } catch (error) {
      const reason = error instanceof Error ? error.message : String(error)
      if (existsSync(stage)) this.moveToQuarantine(stage, manifest.bundleId, manifest.version, reason)
      throw error
    }
  }

  activate(bundleId: string, version: string): AcceleratorBundleSnapshot {
    this.assertMaintenanceWindow()
    this.assertIdentity(bundleId, version)
    const target = join(this.installedRoot, bundleId, version)
    if (!existsSync(target)) throw new Error('Installed accelerator bundle was not found.')
    const record = this.recordFromPath(target, 'installed')
    this.validateCompatibility(record.manifest)
    this.runProviderInventory(record.manifest, target)
    const previous = this.activePointer()
    const history = previous
      ? [...previous.history, { bundleId: previous.bundleId, version: previous.version, profile: previous.profile }]
      : []
    const pointer: ActivePointer = {
      schemaVersion: 1,
      bundleId,
      version,
      profile: record.profile,
      entrypoint: record.manifest.engine.entrypoint,
      engineSha256: record.manifest.engine.sha256.toLowerCase(),
      activatedAt: new Date().toISOString(),
      history: history.slice(-10),
    }
    this.writeActivePointer(pointer)
    this.jobs.resetEngineRuntime()
    return this.snapshot()
  }

  rollback(): AcceleratorBundleSnapshot {
    this.assertMaintenanceWindow()
    const current = this.activePointer()
    if (!current) throw new Error('No accelerator bundle is active.')
    const history = [...current.history]
    while (history.length) {
      const candidate = history.pop()!
      const target = join(this.installedRoot, candidate.bundleId, candidate.version)
      if (!existsSync(target)) continue
      const record = this.recordFromPath(target, 'installed')
      this.validateCompatibility(record.manifest)
      this.runProviderInventory(record.manifest, target)
      this.writeActivePointer({
        schemaVersion: 1,
        bundleId: record.bundleId,
        version: record.version,
        profile: record.profile,
        entrypoint: record.manifest.engine.entrypoint,
        engineSha256: record.manifest.engine.sha256.toLowerCase(),
        activatedAt: new Date().toISOString(),
        history,
      })
      this.jobs.resetEngineRuntime()
      return this.snapshot()
    }
    rmSync(this.activePath, { force: true })
    this.jobs.resetEngineRuntime()
    return this.snapshot()
  }

  quarantine(bundleId: string, version: string, reason: string): AcceleratorBundleSnapshot {
    this.assertMaintenanceWindow()
    this.assertIdentity(bundleId, version)
    const target = join(this.installedRoot, bundleId, version)
    if (!existsSync(target)) throw new Error('Installed accelerator bundle was not found.')
    const active = this.activePointer()
    if (active?.bundleId === bundleId && active.version === version) rmSync(this.activePath, { force: true })
    this.moveToQuarantine(target, bundleId, version, reason.slice(0, 1000) || 'Manually quarantined.')
    this.jobs.resetEngineRuntime()
    return this.snapshot()
  }

  remove(bundleId: string, version: string): AcceleratorBundleSnapshot {
    this.assertMaintenanceWindow()
    this.assertIdentity(bundleId, version)
    const active = this.activePointer()
    if (active?.bundleId === bundleId && active.version === version) throw new Error('Rollback or quarantine the active accelerator bundle before removing it.')
    rmSync(join(this.installedRoot, bundleId, version), { recursive: true, force: true })
    return this.snapshot()
  }

  private verifyAndCopyFiles(manifest: AcceleratorBundleManifest, sourceRoot: string, stage: string, rawManifest: string): AcceleratorBundleVerification {
    for (const file of manifest.files) {
      const source = safeInside(sourceRoot, file.path)
      if (!existsSync(source)) throw new Error(`Bundle file is missing: ${file.path}`)
      const sourceStat = lstatSync(source)
      if (sourceStat.isSymbolicLink() || !sourceStat.isFile()) throw new Error(`Bundle inventory entry is not a regular file: ${file.path}`)
      if (sourceStat.size !== file.sizeBytes) throw new Error(`Bundle file size mismatch: ${file.path}`)
      if (sha256File(source) !== file.sha256.toLowerCase()) throw new Error(`Bundle file SHA-256 mismatch: ${file.path}`)
      const destination = safeInside(stage, file.path)
      mkdirSync(dirname(destination), { recursive: true })
      copyFileSync(source, destination)
      chmodSync(destination, sourceStat.mode)
    }
    const entrypoint = safeInside(stage, manifest.engine.entrypoint)
    if (sha256File(entrypoint) !== manifest.engine.sha256.toLowerCase()) throw new Error('Engine entrypoint hash does not match the manifest.')
    writeFileSync(join(stage, 'accelerator-bundle-manifest.json'), rawManifest, 'utf8')
    return {
      schemaVersion: 1,
      verifiedAt: new Date().toISOString(),
      manifestSha256: sha256Text(rawManifest),
      signatureVerified: true,
      filesVerified: manifest.files.length,
      providerSelfTestPassed: false,
      warnings: [],
    }
  }

  private runProviderInventory(manifest: AcceleratorBundleManifest, root: string): Record<string, unknown> {
    const entrypoint = safeInside(root, manifest.engine.entrypoint)
    if (!existsSync(entrypoint) || sha256File(entrypoint) !== manifest.engine.sha256.toLowerCase()) throw new Error('Installed engine entrypoint failed integrity verification.')
    const completed = spawnSync(entrypoint, [], {
      cwd: dirname(entrypoint),
      input: `${JSON.stringify({ operation: 'providers', job_id: 'bundle-install-self-test' })}\n`,
      encoding: 'utf8',
      timeout: 30_000,
      windowsHide: true,
      shell: false,
    })
    if (completed.error) throw completed.error
    if (completed.status !== 0) throw new Error(`Accelerator engine self-test exited with code ${completed.status ?? 'unknown'}: ${completed.stderr}`)
    const events = completed.stdout.split(/\r?\n/u).filter(Boolean).map(line => JSON.parse(line) as Record<string, unknown>)
    const result = [...events].reverse().find(event => event.type === 'result')
    const inventory = result?.data
    if (!inventory || typeof inventory !== 'object') throw new Error('Accelerator engine did not return provider inventory.')
    const available = (inventory as Record<string, unknown>).available_providers
    if (!Array.isArray(available)) throw new Error('Accelerator engine provider inventory is invalid.')
    const expected = providerFor(manifest.profile)
    if (!available.includes(expected)) throw new Error(`Accelerator engine did not register ${expected}.`)
    for (const provider of manifest.engine.requiredProviders) if (!available.includes(provider)) throw new Error(`Required provider is absent after installation: ${provider}`)
    const runtimeVersion = String((inventory as Record<string, unknown>).runtime_version ?? '')
    if (runtimeVersion !== manifest.engine.onnxRuntimeVersion) throw new Error(`ONNX Runtime version mismatch: expected ${manifest.engine.onnxRuntimeVersion}, received ${runtimeVersion || 'unknown'}.`)
    return inventory as Record<string, unknown>
  }

  private validateCompatibility(manifest: AcceleratorBundleManifest): void {
    if (manifest.platform !== process.platform || manifest.arch !== process.arch) throw new Error(`Bundle targets ${manifest.platform}/${manifest.arch}, but this host is ${process.platform}/${process.arch}.`)
    if (!profileSupportsHost(manifest.profile, process.platform)) throw new Error(`${manifest.profile} is not supported on ${process.platform}.`)
    if (compareVersions(this.appVersion, manifest.appVersion.minimum) < 0) throw new Error(`Bundle requires Studio ${manifest.appVersion.minimum} or newer.`)
    if (manifest.appVersion.maximum && compareVersions(this.appVersion, manifest.appVersion.maximum) > 0) throw new Error(`Bundle supports Studio through ${manifest.appVersion.maximum}.`)
    const expected = providerFor(manifest.profile)
    if (!manifest.engine.requiredProviders.includes(expected)) throw new Error(`Bundle manifest does not require its profile provider ${expected}.`)
    if (manifest.runtimeRequirements.minimumOsVersion && compareVersions(release(), manifest.runtimeRequirements.minimumOsVersion) < 0) throw new Error(`Bundle requires OS version ${manifest.runtimeRequirements.minimumOsVersion} or newer.`)
    if (manifest.profile === 'cuda') {
      const cudaDistribution = Object.entries(manifest.engine.distributions).find(([name]) => name.startsWith('nvidia-cuda-runtime-cu'))
      const cudnnDistribution = Object.entries(manifest.engine.distributions).find(([name]) => name.startsWith('nvidia-cudnn-cu'))
      const cudaMajor = parseMajor(cudaDistribution?.[0])
      const cudnnMajor = parseMajor(cudnnDistribution?.[1])
      if (manifest.runtimeRequirements.cudaMajor && cudaMajor !== manifest.runtimeRequirements.cudaMajor) throw new Error('CUDA runtime distribution does not match manifest requirements.')
      if (manifest.runtimeRequirements.cudnnMajor && cudnnMajor !== manifest.runtimeRequirements.cudnnMajor) throw new Error('cuDNN distribution does not match manifest requirements.')
      const driver = this.nvidiaDriver()
      if (manifest.runtimeRequirements.minimumNvidiaDriver && (!driver || compareVersions(driver, manifest.runtimeRequirements.minimumNvidiaDriver) < 0)) throw new Error(`CUDA bundle requires NVIDIA driver ${manifest.runtimeRequirements.minimumNvidiaDriver} or newer.`)
    }
  }

  private verifyManifestSignature(manifest: AcceleratorBundleManifest): void {
    const expected = canonicalAcceleratorBundlePayload(manifest)
    if (manifest.signedPayload !== expected) throw new Error('Accelerator bundle signed payload does not match manifest fields.')
    const keyPath = this.trustKeyPath()
    if (!keyPath) throw new Error('No trusted accelerator bundle Ed25519 public key is installed.')
    let valid = false
    try {
      valid = verify(null, Buffer.from(expected, 'utf8'), readFileSync(keyPath), Buffer.from(manifest.signature, 'base64'))
    } catch (error) {
      throw new Error(`Accelerator bundle trust key could not verify the manifest: ${error instanceof Error ? error.message : String(error)}`)
    }
    if (!valid) throw new Error('Accelerator bundle Ed25519 signature verification failed.')
  }

  private trustKeyPath(): string | undefined {
    const candidates = [
      join(this.userDataPath, 'accelerator-bundle-public-key.pem'),
      join(this.resourcesPath, 'accelerator-bundle-public-key.pem'),
      join(this.userDataPath, 'update-public-key.pem'),
      join(this.resourcesPath, 'update-public-key.pem'),
    ]
    return candidates.find(path => existsSync(path) && statSync(path).isFile())
  }

  private nvidiaDriver(): string | undefined {
    try {
      const output = execFileSync('nvidia-smi', ['--query-gpu=driver_version', '--format=csv,noheader'], { encoding: 'utf8', timeout: 5000, windowsHide: true })
      return output.trim().split(/\r?\n/u).find(Boolean)
    } catch { return undefined }
  }

  private activePointer(): ActivePointer | undefined {
    const pointer = readJson<ActivePointer>(this.activePath)
    if (!pointer || pointer.schemaVersion !== 1 || !idPattern.test(pointer.bundleId) || !semverPattern.test(pointer.version)) return undefined
    return pointer
  }

  private writeActivePointer(pointer: ActivePointer): void {
    mkdirSync(dirname(this.activePath), { recursive: true })
    const temporary = `${this.activePath}.${randomUUID()}.tmp`
    writeFileSync(temporary, `${JSON.stringify(pointer, null, 2)}\n`, 'utf8')
    renameSync(temporary, this.activePath)
  }

  private scanRecords(root: string, state: 'installed' | 'quarantined'): AcceleratorBundleRecord[] {
    if (!existsSync(root)) return []
    const records: AcceleratorBundleRecord[] = []
    const walk = (directory: string) => {
      for (const entry of readdirSync(directory, { withFileTypes: true })) {
        if (!entry.isDirectory()) continue
        const child = join(directory, entry.name)
        const manifestPath = join(child, 'accelerator-bundle-manifest.json')
        if (existsSync(manifestPath)) {
          try { records.push(this.recordFromPath(child, state)) } catch { /* corrupt records stay isolated until manual cleanup */ }
        } else walk(child)
      }
    }
    walk(root)
    return records.sort((left, right) => `${left.bundleId}@${left.version}`.localeCompare(`${right.bundleId}@${right.version}`))
  }

  private recordFromPath(path: string, state: 'installed' | 'quarantined'): AcceleratorBundleRecord {
    const manifest = acceleratorBundleManifestSchema.parse(JSON.parse(readFileSync(join(path, 'accelerator-bundle-manifest.json'), 'utf8'))) as AcceleratorBundleManifest
    const verification = readJson<AcceleratorBundleVerification>(join(path, 'verification.json'))
    const quarantineReason = existsSync(join(path, 'quarantine-reason.txt')) ? readFileSync(join(path, 'quarantine-reason.txt'), 'utf8').trim() : undefined
    return {
      bundleId: manifest.bundleId,
      version: manifest.version,
      profile: manifest.profile,
      platform: manifest.platform,
      arch: manifest.arch,
      state,
      installedAt: verification?.verifiedAt ?? statSync(path).mtime.toISOString(),
      path,
      manifest,
      verification,
      quarantineReason,
    }
  }

  private moveToQuarantine(source: string, bundleId: string, version: string, reason: string): void {
    const target = join(this.quarantineRoot, bundleId, `${version}-${Date.now()}`)
    mkdirSync(dirname(target), { recursive: true })
    writeFileSync(join(source, 'quarantine-reason.txt'), `${reason}\n`, 'utf8')
    renameSync(source, target)
  }

  private removeAbandonedStaging(): void {
    if (!existsSync(this.stagingRoot)) return
    for (const entry of readdirSync(this.stagingRoot, { withFileTypes: true })) {
      if (entry.isDirectory()) rmSync(join(this.stagingRoot, entry.name), { recursive: true, force: true })
    }
  }

  private assertMaintenanceWindow(): void {
    if (this.jobs.activeCount() > 0) throw new Error('Pause or finish active and queued jobs before changing the accelerator engine bundle.')
  }

  private assertIdentity(bundleId: string, version: string): void {
    if (!idPattern.test(bundleId) || !semverPattern.test(version)) throw new Error('Invalid accelerator bundle identity.')
  }
}
