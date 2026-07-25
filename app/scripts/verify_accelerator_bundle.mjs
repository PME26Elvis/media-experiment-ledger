#!/usr/bin/env node
import { createHash, verify } from 'node:crypto'
import { existsSync, readFileSync, statSync } from 'node:fs'
import { isAbsolute, join, normalize, resolve, sep } from 'node:path'
import process from 'node:process'

const root = resolve(process.argv[2] ?? '')
const keyPath = resolve(process.argv[3] ?? '')
if (!existsSync(root) || !existsSync(keyPath)) throw new Error('Usage: verify_accelerator_bundle.mjs <bundle-root> <public-key.pem>')
const manifestPath = join(root, 'accelerator-bundle-manifest.json')
const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'))
const safe = value => {
  const normalized = normalize(value)
  if (isAbsolute(value) || normalized === '..' || normalized.startsWith(`..${sep}`)) throw new Error(`Unsafe path: ${value}`)
  return resolve(root, normalized)
}
const hash = path => createHash('sha256').update(readFileSync(path)).digest('hex')
const files = [...manifest.files].sort((left, right) => left.path.localeCompare(right.path)).map(file => ({
  path: file.path,
  sizeBytes: file.sizeBytes,
  sha256: file.sha256.toLowerCase(),
  kind: file.kind,
}))
const payload = JSON.stringify({
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
if (manifest.signedPayload !== payload) throw new Error('Signed payload does not match manifest fields')
if (!verify(null, Buffer.from(payload, 'utf8'), readFileSync(keyPath), Buffer.from(manifest.signature, 'base64'))) throw new Error('Ed25519 signature verification failed')
for (const file of files) {
  const path = safe(file.path)
  if (!existsSync(path) || !statSync(path).isFile()) throw new Error(`Missing file: ${file.path}`)
  if (statSync(path).size !== file.sizeBytes) throw new Error(`Size mismatch: ${file.path}`)
  if (hash(path) !== file.sha256) throw new Error(`SHA-256 mismatch: ${file.path}`)
}
const entrypoint = safe(manifest.engine.entrypoint)
if (hash(entrypoint) !== manifest.engine.sha256.toLowerCase()) throw new Error('Engine entrypoint hash mismatch')
for (const required of [manifest.sbomFile, manifest.noticesFile, manifest.nativeInventoryFile]) if (!files.some(file => file.path === required)) throw new Error(`Required evidence file is not inventoried: ${required}`)
console.log(JSON.stringify({ verified: true, bundleId: manifest.bundleId, version: manifest.version, profile: manifest.profile, files: files.length }, null, 2))
