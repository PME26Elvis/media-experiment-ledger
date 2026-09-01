import { createHash, randomUUID } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { join, resolve } from 'node:path'

const appRoot = resolve(import.meta.dirname, '..')
const repoRoot = resolve(appRoot, '..')
const outputRoot = join(appRoot, 'release-evidence')
const packageJson = JSON.parse(await readFile(join(appRoot, 'package.json'), 'utf8'))
const packageLock = JSON.parse(await readFile(join(appRoot, 'package-lock.json'), 'utf8'))
const contractText = await readFile(join(repoRoot, 'app-product-contract.json'), 'utf8')

function sha256(value) {
  return createHash('sha256').update(value).digest('hex')
}

function dependencyName(path, record) {
  if (record.name) return record.name
  const marker = 'node_modules/'
  const index = path.lastIndexOf(marker)
  if (index < 0) return path
  const remainder = path.slice(index + marker.length)
  if (remainder.startsWith('@')) return remainder.split('/').slice(0, 2).join('/')
  return remainder.split('/')[0]
}

const records = Object.entries(packageLock.packages ?? {})
  .filter(([path, record]) => path && record?.version)
  .map(([path, record]) => ({
    path,
    name: dependencyName(path, record),
    version: String(record.version),
    license: record.license ? String(record.license) : 'NOASSERTION',
    resolved: record.resolved ? String(record.resolved) : undefined,
    integrity: record.integrity ? String(record.integrity) : undefined,
    dev: Boolean(record.dev),
    optional: Boolean(record.optional),
  }))
  .sort((a, b) => a.name.localeCompare(b.name) || a.version.localeCompare(b.version))

const production = records.filter((record) => !record.dev)
const sbom = {
  bomFormat: 'CycloneDX',
  specVersion: '1.5',
  serialNumber: `urn:uuid:${randomUUID()}`,
  version: 1,
  metadata: {
    timestamp: new Date().toISOString(),
    component: {
      type: 'application',
      name: packageJson.name,
      version: packageJson.version,
      licenses: [{ license: { id: 'Apache-2.0' } }],
      purl: `pkg:npm/${encodeURIComponent(packageJson.name)}@${packageJson.version}`,
    },
    properties: [
      { name: 'mel:git-sha', value: process.env.GITHUB_SHA ?? 'local' },
      { name: 'mel:contract-sha256', value: sha256(contractText) },
      { name: 'mel:package-lock-sha256', value: sha256(JSON.stringify(packageLock)) },
    ],
  },
  components: production.map((record) => ({
    type: 'library',
    name: record.name,
    version: record.version,
    purl: `pkg:npm/${encodeURIComponent(record.name)}@${record.version}`,
    licenses: record.license === 'NOASSERTION'
      ? [{ license: { name: 'NOASSERTION' } }]
      : [{ expression: record.license }],
    hashes: record.integrity?.startsWith('sha512-')
      ? [{ alg: 'SHA-512', content: record.integrity.slice('sha512-'.length) }]
      : undefined,
    externalReferences: record.resolved
      ? [{ type: 'distribution', url: record.resolved }]
      : undefined,
    properties: [
      { name: 'mel:lock-path', value: record.path },
      { name: 'mel:optional', value: String(record.optional) },
    ],
  })),
}

const notices = {
  schema_version: 1,
  generated_at: new Date().toISOString(),
  application: {
    name: packageJson.name,
    version: packageJson.version,
    license: 'Apache-2.0',
  },
  dependency_count: records.length,
  production_dependency_count: production.length,
  dependencies: records,
  policy: {
    model_weights_separate: true,
    sample_data_separate: true,
    unknown_rights_default: 'do_not_distribute',
  },
}

const buildInput = {
  schema_version: 1,
  generated_at: new Date().toISOString(),
  git_sha: process.env.GITHUB_SHA ?? 'local',
  app_version: packageJson.version,
  node_version: process.version,
  platform: process.platform,
  architecture: process.arch,
  contract_sha256: sha256(contractText),
  package_lock_sha256: sha256(JSON.stringify(packageLock)),
  production_dependency_count: production.length,
}

await mkdir(outputRoot, { recursive: true })
await Promise.all([
  writeFile(join(outputRoot, 'sbom.cdx.json'), `${JSON.stringify(sbom, null, 2)}\n`),
  writeFile(join(outputRoot, 'third-party-notices.json'), `${JSON.stringify(notices, null, 2)}\n`),
  writeFile(join(outputRoot, 'build-input-manifest.json'), `${JSON.stringify(buildInput, null, 2)}\n`),
])
console.log(JSON.stringify({ outputRoot, components: production.length }, null, 2))
