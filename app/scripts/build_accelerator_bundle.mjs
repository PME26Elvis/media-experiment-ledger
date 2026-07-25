#!/usr/bin/env node
import { createHash, generateKeyPairSync, sign, verify } from 'node:crypto'
import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs'
import { basename, dirname, join, relative, resolve, sep } from 'node:path'
import process from 'node:process'

function argumentsMap(argv) {
  const values = new Map()
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index]
    if (!token.startsWith('--')) continue
    const name = token.slice(2)
    const next = argv[index + 1]
    if (!next || next.startsWith('--')) values.set(name, true)
    else { values.set(name, next); index += 1 }
  }
  return values
}

function required(values, key) {
  const value = values.get(key)
  if (typeof value !== 'string' || !value.trim()) throw new Error(`--${key} is required`)
  return value.trim()
}

function sha256(path) {
  return createHash('sha256').update(readFileSync(path)).digest('hex')
}

function walk(root) {
  const files = []
  const visit = directory => {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const path = join(directory, entry.name)
      if (entry.isSymbolicLink()) throw new Error(`Symlinks are not allowed in accelerator bundles: ${path}`)
      if (entry.isDirectory()) visit(path)
      else if (entry.isFile()) files.push(path)
    }
  }
  visit(root)
  return files.sort()
}

function safeRelative(root, path) {
  const value = relative(resolve(root), resolve(path))
  if (!value || value === '..' || value.startsWith(`..${sep}`)) throw new Error(`File escapes bundle root: ${path}`)
  return value.split(sep).join('/')
}

function classify(path, entrypoint) {
  if (path === entrypoint) return 'engine'
  if (/\.(?:dll|so(?:\.\d+)*|dylib|pyd)$/iu.test(path)) return 'native'
  if (/sbom/i.test(path)) return 'sbom'
  if (/(?:notice|license|copying)/iu.test(path)) return 'license'
  return 'metadata'
}

function canonicalPayload(manifest) {
  const files = [...manifest.files].sort((left, right) => left.path.localeCompare(right.path)).map(file => ({
    path: file.path,
    sizeBytes: file.sizeBytes,
    sha256: file.sha256.toLowerCase(),
    kind: file.kind,
  }))
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
    files,
    sbomFile: manifest.sbomFile,
    noticesFile: manifest.noticesFile,
    nativeInventoryFile: manifest.nativeInventoryFile,
  })
}

const values = argumentsMap(process.argv.slice(2))
const engineRoot = resolve(required(values, 'engine-root'))
const outputRoot = resolve(required(values, 'output'))
const profile = required(values, 'profile')
const bundleId = required(values, 'bundle-id')
const version = required(values, 'version')
const appMinimum = required(values, 'app-minimum')
const appMaximum = values.get('app-maximum')
const platform = values.get('platform') || process.platform
const arch = values.get('arch') || process.arch
const minimumOsVersion = values.get('minimum-os-version')
const minimumNvidiaDriver = values.get('minimum-nvidia-driver')
const cudaMajor = values.get('cuda-major') ? Number(values.get('cuda-major')) : undefined
const cudnnMajor = values.get('cudnn-major') ? Number(values.get('cudnn-major')) : undefined

if (!['directml', 'cuda', 'coreml'].includes(profile)) throw new Error(`Unsupported profile: ${profile}`)
if (!existsSync(engineRoot) || !statSync(engineRoot).isDirectory()) throw new Error(`Engine root does not exist: ${engineRoot}`)
mkdirSync(outputRoot, { recursive: true })
const bundleEngineRoot = join(outputRoot, 'engine')
cpSync(engineRoot, bundleEngineRoot, { recursive: true, errorOnExist: false, force: true })

const buildManifestPath = join(bundleEngineRoot, 'engine-build-manifest.json')
if (!existsSync(buildManifestPath)) throw new Error('engine-build-manifest.json is required in the engine root')
const buildManifest = JSON.parse(readFileSync(buildManifestPath, 'utf8'))
const executableName = platform === 'win32' ? 'mel-engine.exe' : 'mel-engine'
const entrypointPath = join(bundleEngineRoot, executableName)
if (!existsSync(entrypointPath)) throw new Error(`Engine entrypoint is missing: ${entrypointPath}`)
const entrypoint = safeRelative(outputRoot, entrypointPath)
const provider = profile === 'directml' ? 'DmlExecutionProvider' : profile === 'cuda' ? 'CUDAExecutionProvider' : 'CoreMLExecutionProvider'
const inventory = buildManifest.provider_inventory ?? {}
if (!Array.isArray(inventory.available_providers) || !inventory.available_providers.includes(provider)) throw new Error(`Built engine did not register ${provider}`)

const nativeFiles = walk(bundleEngineRoot).filter(path => /\.(?:dll|so(?:\.\d+)*|dylib|pyd)$/iu.test(path)).map(path => ({
  path: safeRelative(outputRoot, path),
  sizeBytes: statSync(path).size,
  sha256: sha256(path),
}))
const nativeInventoryPath = join(outputRoot, 'native-library-inventory.json')
writeFileSync(nativeInventoryPath, `${JSON.stringify({ schemaVersion: 1, profile, generatedAt: new Date().toISOString(), libraries: nativeFiles }, null, 2)}\n`, 'utf8')

const sbomPath = join(outputRoot, 'SBOM.spdx.json')
writeFileSync(sbomPath, `${JSON.stringify({
  spdxVersion: 'SPDX-2.3',
  dataLicense: 'CC0-1.0',
  SPDXID: 'SPDXRef-DOCUMENT',
  name: `${bundleId}-${version}`,
  documentNamespace: `https://github.com/PME26Elvis/media-experiment-ledger/accelerator-bundles/${bundleId}/${version}`,
  creationInfo: { created: new Date().toISOString(), creators: ['Tool: Media Experiment Ledger accelerator bundle builder'] },
  packages: Object.entries(buildManifest.build_distributions ?? {}).map(([name, packageVersion], index) => ({
    name,
    SPDXID: `SPDXRef-Package-${index + 1}`,
    versionInfo: packageVersion,
    downloadLocation: 'NOASSERTION',
    filesAnalyzed: false,
    licenseConcluded: 'NOASSERTION',
    licenseDeclared: 'NOASSERTION',
  })),
}, null, 2)}\n`, 'utf8')

const noticesPath = join(outputRoot, 'THIRD_PARTY_NOTICES.txt')
writeFileSync(noticesPath, [
  'Media Experiment Ledger Studio optional accelerator engine bundle',
  `Profile: ${profile}`,
  `ONNX Runtime: ${inventory.runtime_version ?? 'unknown'}`,
  '',
  'Redistribution is permitted only when every included runtime and native library license allows it.',
  'The SPDX SBOM and native-library inventory are authoritative evidence inputs; they are not a substitute for legal review.',
  '',
  ...Object.entries(buildManifest.build_distributions ?? {}).map(([name, packageVersion]) => `${name} ${packageVersion}`),
  '',
].join('\n'), 'utf8')

const files = walk(outputRoot)
  .filter(path => basename(path) !== 'accelerator-bundle-manifest.json' && basename(path) !== 'DEVELOPMENT-PUBLIC-KEY.pem')
  .map(path => {
    const relativePath = safeRelative(outputRoot, path)
    return { path: relativePath, sizeBytes: statSync(path).size, sha256: sha256(path), kind: classify(relativePath, entrypoint) }
  })

const manifest = {
  schemaVersion: 1,
  bundleId,
  version,
  profile,
  platform,
  arch,
  appVersion: { minimum: appMinimum, ...(typeof appMaximum === 'string' ? { maximum: appMaximum } : {}) },
  engine: {
    entrypoint,
    sha256: sha256(entrypointPath),
    onnxRuntimeVersion: String(inventory.runtime_version ?? ''),
    requiredProviders: [provider, 'CPUExecutionProvider'],
    distributions: buildManifest.build_distributions ?? inventory.distributions ?? {},
  },
  runtimeRequirements: {
    ...(typeof minimumOsVersion === 'string' ? { minimumOsVersion } : {}),
    ...(typeof minimumNvidiaDriver === 'string' ? { minimumNvidiaDriver } : {}),
    ...(Number.isInteger(cudaMajor) ? { cudaMajor } : {}),
    ...(Number.isInteger(cudnnMajor) ? { cudnnMajor } : {}),
  },
  files,
  sbomFile: safeRelative(outputRoot, sbomPath),
  noticesFile: safeRelative(outputRoot, noticesPath),
  nativeInventoryFile: safeRelative(outputRoot, nativeInventoryPath),
  signedPayload: '',
  signature: '',
}
manifest.signedPayload = canonicalPayload(manifest)

let privateKey
let publicKey
const privateKeyPath = values.get('private-key')
if (typeof privateKeyPath === 'string') {
  privateKey = readFileSync(resolve(privateKeyPath))
} else if (process.env.ACCELERATOR_BUNDLE_PRIVATE_KEY) {
  privateKey = Buffer.from(process.env.ACCELERATOR_BUNDLE_PRIVATE_KEY.replace(/\\n/gu, '\n'), 'utf8')
} else if (values.get('development-key') === true) {
  const pair = generateKeyPairSync('ed25519')
  privateKey = pair.privateKey.export({ type: 'pkcs8', format: 'pem' })
  publicKey = pair.publicKey.export({ type: 'spki', format: 'pem' })
  writeFileSync(join(outputRoot, 'DEVELOPMENT-PUBLIC-KEY.pem'), publicKey)
} else {
  throw new Error('A production Ed25519 private key is required. Use --development-key only for non-publishable CI evidence.')
}
manifest.signature = sign(null, Buffer.from(manifest.signedPayload, 'utf8'), privateKey).toString('base64')
if (publicKey && !verify(null, Buffer.from(manifest.signedPayload, 'utf8'), publicKey, Buffer.from(manifest.signature, 'base64'))) throw new Error('Development signature self-verification failed')

const manifestPath = join(outputRoot, 'accelerator-bundle-manifest.json')
writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8')
writeFileSync(join(outputRoot, 'bundle-build-evidence.json'), `${JSON.stringify({
  schemaVersion: 1,
  bundleId,
  version,
  profile,
  platform,
  arch,
  manifestSha256: sha256(manifestPath),
  fileCount: files.length,
  totalBytes: files.reduce((sum, file) => sum + file.sizeBytes, 0),
  developmentSignature: typeof privateKeyPath !== 'string' && !process.env.ACCELERATOR_BUNDLE_PRIVATE_KEY,
  generatedAt: new Date().toISOString(),
}, null, 2)}\n`, 'utf8')
console.log(JSON.stringify({ manifestPath, bundleId, version, profile, files: files.length, provider, runtime: manifest.engine.onnxRuntimeVersion }, null, 2))
