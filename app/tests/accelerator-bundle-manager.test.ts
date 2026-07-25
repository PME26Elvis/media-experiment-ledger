import { generateKeyPairSync, sign, createHash } from 'node:crypto'
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, relative, sep } from 'node:path'
import type { AcceleratorBundleManifest, AcceleratorBundleProfile } from '../src/shared/accelerator-bundle-contracts'
import {
  AcceleratorBundleManager,
  acceleratorBundleManifestSchema,
  canonicalAcceleratorBundlePayload,
  compareVersions,
} from '../src/main/accelerator-bundle-manager'

function hash(path: string): string {
  return createHash('sha256').update(readFileSync(path)).digest('hex')
}

function profileForHost(): { profile: AcceleratorBundleProfile; provider: string } {
  if (process.platform === 'win32') return { profile: 'directml', provider: 'DmlExecutionProvider' }
  if (process.platform === 'darwin') return { profile: 'coreml', provider: 'CoreMLExecutionProvider' }
  return { profile: 'cuda', provider: 'CUDAExecutionProvider' }
}

function writeExecutable(root: string, provider: string, runtime = '1.22.1'): string {
  const data = JSON.stringify({ type: 'result', data: { runtime_version: runtime, available_providers: [provider, 'CPUExecutionProvider'], provider_support: {} } })
  if (process.platform === 'win32') {
    const script = join(root, 'provider.cjs')
    const command = join(root, 'mel-engine.cmd')
    writeFileSync(script, `console.log(${JSON.stringify(data)})\n`, 'utf8')
    writeFileSync(command, `@node "%~dp0\\provider.cjs"\r\n`, 'utf8')
    return command
  }
  const executable = join(root, 'mel-engine')
  writeFileSync(executable, `#!/usr/bin/env node\nconsole.log(${JSON.stringify(data)})\n`, 'utf8')
  chmodSync(executable, 0o755)
  return executable
}

function createBundle(root: string, version: string, privateKey: ReturnType<typeof generateKeyPairSync>['privateKey']) {
  const { profile, provider } = profileForHost()
  const source = join(root, `source-${version}`)
  const engineRoot = join(source, 'engine')
  mkdirSync(engineRoot, { recursive: true })
  const executable = writeExecutable(engineRoot, provider)
  const sbom = join(source, 'SBOM.spdx.json')
  const notices = join(source, 'THIRD_PARTY_NOTICES.txt')
  const native = join(source, 'native-library-inventory.json')
  writeFileSync(sbom, '{"spdxVersion":"SPDX-2.3"}\n', 'utf8')
  writeFileSync(notices, 'test notices\n', 'utf8')
  writeFileSync(native, '{"libraries":[]}\n', 'utf8')
  const paths = [executable, sbom, notices, native]
  const relativePath = (path: string) => relative(source, path).split(sep).join('/')
  const distributions = profile === 'cuda'
    ? { 'onnxruntime-gpu': '1.22.1', 'nvidia-cuda-runtime-cu12': '12.9.79', 'nvidia-cudnn-cu12': '9.10.2.21' }
    : { onnxruntime: '1.22.1' }
  const manifest = {
    schemaVersion: 1,
    bundleId: `mel-${profile}-${process.platform}-${process.arch}`,
    version,
    profile,
    platform: process.platform,
    arch: process.arch,
    appVersion: { minimum: '1.0.0-rc.1', maximum: '1.0.0' },
    engine: {
      entrypoint: relativePath(executable),
      sha256: hash(executable),
      onnxRuntimeVersion: '1.22.1',
      requiredProviders: [provider, 'CPUExecutionProvider'],
      distributions,
    },
    runtimeRequirements: profile === 'cuda' ? { cudaMajor: 12, cudnnMajor: 9 } : {},
    files: paths.map(path => ({
      path: relativePath(path),
      sizeBytes: statSync(path).size,
      sha256: hash(path),
      kind: path === executable ? 'engine' as const : path === sbom ? 'sbom' as const : path === notices ? 'license' as const : 'metadata' as const,
    })),
    sbomFile: relativePath(sbom),
    noticesFile: relativePath(notices),
    nativeInventoryFile: relativePath(native),
    signedPayload: '',
    signature: '',
  } satisfies AcceleratorBundleManifest
  manifest.signedPayload = canonicalAcceleratorBundlePayload(manifest)
  manifest.signature = sign(null, Buffer.from(manifest.signedPayload, 'utf8'), privateKey).toString('base64')
  const manifestPath = join(source, 'accelerator-bundle-manifest.json')
  writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8')
  return { manifest, manifestPath, executable }
}

describe('AcceleratorBundleManager', () => {
  let root = ''
  beforeEach(() => { root = mkdtempSync(join(tmpdir(), 'mel-accelerator-bundle-')) })
  afterEach(() => { rmSync(root, { recursive: true, force: true }) })

  it('uses deterministic canonical payloads and rejects duplicate inventory paths', () => {
    const pair = generateKeyPairSync('ed25519')
    const created = createBundle(root, '1.0.0-rc.6', pair.privateKey)
    expect(canonicalAcceleratorBundlePayload(created.manifest)).toBe(created.manifest.signedPayload)
    const duplicate = { ...created.manifest, files: [...created.manifest.files, created.manifest.files[0]] }
    expect(acceleratorBundleManifestSchema.safeParse(duplicate).success).toBe(false)
  })

  it('compares release-candidate version cores for compatibility gates', () => {
    expect(compareVersions('1.0.0-rc.6', '1.0.0-rc.1')).toBe(0)
    expect(compareVersions('1.1.0', '1.0.9')).toBeGreaterThan(0)
    expect(compareVersions('0.9.9', '1.0.0')).toBeLessThan(0)
  })

  it('installs, activates and rolls back verified bundles atomically', () => {
    const pair = generateKeyPairSync('ed25519')
    writeFileSync(join(root, 'accelerator-bundle-public-key.pem'), pair.publicKey.export({ type: 'spki', format: 'pem' }))
    const jobs = { activeCount: () => 0, resetEngineRuntime: vi.fn() }
    const manager = new AcceleratorBundleManager(root, root, '1.0.0-rc.6', jobs)
    const first = createBundle(root, '1.0.0-rc.1', pair.privateKey)
    const second = createBundle(root, '1.0.0-rc.2', pair.privateKey)
    expect(manager.install(first.manifestPath).verification?.providerSelfTestPassed).toBe(true)
    manager.activate(first.manifest.bundleId, first.manifest.version)
    manager.install(second.manifestPath)
    expect(manager.activate(second.manifest.bundleId, second.manifest.version).active?.version).toBe('1.0.0-rc.2')
    expect(manager.rollback().active?.version).toBe('1.0.0-rc.1')
    expect(jobs.resetEngineRuntime).toHaveBeenCalledTimes(3)
  })

  it('fails closed on an untrusted signature and refuses maintenance while jobs are active', () => {
    const trusted = generateKeyPairSync('ed25519')
    const untrusted = generateKeyPairSync('ed25519')
    writeFileSync(join(root, 'accelerator-bundle-public-key.pem'), trusted.publicKey.export({ type: 'spki', format: 'pem' }))
    const created = createBundle(root, '1.0.0-rc.6', untrusted.privateKey)
    const manager = new AcceleratorBundleManager(root, root, '1.0.0-rc.6', { activeCount: () => 0, resetEngineRuntime: vi.fn() })
    expect(() => manager.install(created.manifestPath)).toThrow(/signature verification failed/i)
    const blocked = new AcceleratorBundleManager(join(root, 'blocked'), root, '1.0.0-rc.6', { activeCount: () => 1, resetEngineRuntime: vi.fn() })
    expect(() => blocked.install(created.manifestPath)).toThrow(/Pause or finish active and queued jobs/i)
  })
})
