import { createHash, createPrivateKey, sign } from 'node:crypto'
import { readdir, readFile, stat, writeFile } from 'node:fs/promises'
import { basename, join } from 'node:path'
import process from 'node:process'

const [root, version, channel] = process.argv.slice(2)
if (!root || !version || !channel) {
  throw new Error('Usage: node generate_offline_update_manifests.mjs <root> <version> <channel>')
}
if (!/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/u.test(version)) throw new Error(`Invalid version: ${version}`)
if (!['alpha', 'beta', 'stable'].includes(channel)) throw new Error(`Invalid channel: ${channel}`)

const privateKeyPem = process.env.RELEASE_ED25519_PRIVATE_KEY?.trim()
const privateKey = privateKeyPem ? createPrivateKey(privateKeyPem) : undefined
if (privateKey && privateKey.asymmetricKeyType !== 'ed25519') {
  throw new Error(`Expected Ed25519 private key, got ${privateKey.asymmetricKeyType}.`)
}
if (channel === 'stable' && !privateKey) throw new Error('Stable offline manifests require RELEASE_ED25519_PRIVATE_KEY.')

const packagePattern = /-(windows|macos|linux)-(x64|arm64)(?:-(setup|portable))?\.(exe|dmg|zip|AppImage|deb)$/u
const files = (await readdir(root)).filter(name => packagePattern.test(name)).sort()
if (files.length === 0) throw new Error(`No installer packages found below ${root}`)

const mapPlatform = { windows: 'win32', macos: 'darwin', linux: 'linux' }
const manifests = []
for (const name of files) {
  const match = name.match(packagePattern)
  if (!match) continue
  const [, os, arch] = match
  const path = join(root, name)
  const content = await readFile(path)
  const details = await stat(path)
  const payload = {
    schemaVersion: 1,
    version,
    channel,
    platform: mapPlatform[os],
    arch,
    packageFile: basename(name),
    packageSizeBytes: details.size,
    packageSha256: createHash('sha256').update(content).digest('hex'),
  }
  const signedPayload = JSON.stringify(payload)
  const signature = privateKey
    ? sign(null, Buffer.from(signedPayload, 'utf8'), privateKey).toString('base64')
    : undefined
  const manifest = {
    ...payload,
    ...(signature ? { signature, signedPayload } : {}),
  }
  const outputName = `${name}.offline-update.json`
  await writeFile(join(root, outputName), `${JSON.stringify(manifest, null, 2)}\n`, 'utf8')
  manifests.push({ package: name, manifest: outputName, signed: Boolean(signature) })
}
await writeFile(join(root, 'offline-update-index.json'), `${JSON.stringify({
  schemaVersion: 1,
  version,
  channel,
  manifests,
  generatedAt: new Date().toISOString(),
}, null, 2)}\n`, 'utf8')
console.log(JSON.stringify({ manifests: manifests.length, signed: manifests.filter(item => item.signed).length }, null, 2))
