import { safeStorage } from 'electron'
import { randomUUID } from 'node:crypto'
import { mkdirSync, readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import type { SaveSecretProfileRequest, SecretBackend, SecretProfileSummary } from '../shared/contracts'
import { decryptPortableVault, encryptPortableVault, type PortableVaultDocument } from './portable-vault'

interface SecretProfileRecord {
  id: string
  name: string
  provider: string
  environmentVariable: string
  backend: SecretBackend
  envFilePath?: string
  payloadPath?: string
  createdAt: string
  updatedAt: string
}

interface SecretIndex { schemaVersion: 1; profiles: SecretProfileRecord[] }

function atomicJson(path: string, value: unknown): void {
  mkdirSync(dirname(path), { recursive: true })
  const temporary = `${path}.tmp`
  writeFileSync(temporary, JSON.stringify(value, null, 2), { encoding: 'utf8', mode: 0o600 })
  renameSync(temporary, path)
}

function parseEnv(path: string): Map<string, string> {
  const values = new Map<string, string>()
  const content = readFileSync(path, 'utf8')
  for (const rawLine of content.split(/\r?\n/u)) {
    const line = rawLine.trim()
    if (!line || line.startsWith('#')) continue
    const normalized = line.startsWith('export ') ? line.slice(7).trim() : line
    const separator = normalized.indexOf('=')
    if (separator <= 0) continue
    const key = normalized.slice(0, separator).trim()
    let value = normalized.slice(separator + 1).trim()
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) value = value.slice(1, -1)
    values.set(key, value.replace(/\\n/g, '\n'))
  }
  return values
}

export class SecretStore {
  private readonly root: string
  private readonly indexPath: string
  private readonly sessions = new Map<string, string>()
  private readonly unlockedVaults = new Map<string, string>()

  constructor(userDataPath: string) {
    this.root = join(userDataPath, 'secrets')
    this.indexPath = join(this.root, 'index.json')
    mkdirSync(this.root, { recursive: true })
  }

  list(): SecretProfileSummary[] {
    return this.readIndex().profiles.map((profile) => this.summary(profile))
  }

  async save(request: SaveSecretProfileRequest): Promise<SecretProfileSummary> {
    const index = this.readIndex()
    const now = new Date().toISOString()
    const existing = request.id ? index.profiles.find((profile) => profile.id === request.id) : undefined
    const id = existing?.id ?? randomUUID()
    const record: SecretProfileRecord = {
      id,
      name: request.name.trim(),
      provider: request.provider.trim(),
      environmentVariable: request.environmentVariable.trim(),
      backend: request.backend,
      envFilePath: request.backend === 'env' && request.envFilePath ? resolve(request.envFilePath) : undefined,
      createdAt: existing?.createdAt ?? now,
      updatedAt: now,
    }
    if (!record.name || !record.provider || !record.environmentVariable) throw new Error('Name, provider and environment variable are required.')

    if (request.backend === 'session') {
      if (!request.secret) throw new Error('Session secret is required.')
      this.sessions.set(id, request.secret)
    } else if (request.backend === 'env') {
      if (!record.envFilePath) throw new Error('An explicit .env file path is required.')
      const values = parseEnv(record.envFilePath)
      if (!values.get(record.environmentVariable)) throw new Error(`The selected .env file does not contain ${record.environmentVariable}.`)
    } else if (request.backend === 'os') {
      if (!request.secret) throw new Error('Secret value is required.')
      if (!await safeStorage.isAsyncEncryptionAvailable()) throw new Error('OS-backed encryption is unavailable.')
      if (process.platform === 'linux' && safeStorage.getSelectedStorageBackend() === 'basic_text') throw new Error('Linux safeStorage selected basic_text; choose session, .env or portable vault instead.')
      const encrypted = await safeStorage.encryptStringAsync(request.secret)
      record.payloadPath = join(this.root, `${id}.os-secret`)
      writeFileSync(record.payloadPath, encrypted, { mode: 0o600 })
    } else if (request.backend === 'portable-vault') {
      if (!request.secret || !request.password) throw new Error('Secret and portable vault password are required.')
      const document = await encryptPortableVault(request.secret, request.password)
      record.payloadPath = join(this.root, `${id}.portable-vault.json`)
      atomicJson(record.payloadPath, document)
      this.unlockedVaults.set(id, request.secret)
    }

    const profiles = index.profiles.filter((profile) => profile.id !== id)
    profiles.push(record)
    atomicJson(this.indexPath, { schemaVersion: 1, profiles } satisfies SecretIndex)
    return this.summary(record)
  }

  remove(id: string): boolean {
    const index = this.readIndex()
    const profile = index.profiles.find((item) => item.id === id)
    if (!profile) return false
    if (profile.payloadPath) rmSync(profile.payloadPath, { force: true })
    this.sessions.delete(id)
    this.unlockedVaults.delete(id)
    atomicJson(this.indexPath, { schemaVersion: 1, profiles: index.profiles.filter((item) => item.id !== id) } satisfies SecretIndex)
    return true
  }

  async unlock(id: string, password: string): Promise<SecretProfileSummary> {
    const profile = this.requireProfile(id)
    if (profile.backend !== 'portable-vault' || !profile.payloadPath) throw new Error('Profile is not a portable vault.')
    const document = JSON.parse(readFileSync(profile.payloadPath, 'utf8')) as PortableVaultDocument
    this.unlockedVaults.set(id, await decryptPortableVault(document, password))
    return this.summary(profile)
  }

  lock(id: string): SecretProfileSummary {
    const profile = this.requireProfile(id)
    this.unlockedVaults.delete(id)
    if (profile.backend === 'session') this.sessions.delete(id)
    return this.summary(profile)
  }

  async resolveEnvironment(profileId: string | undefined): Promise<Record<string, string>> {
    if (!profileId) return {}
    const profile = this.requireProfile(profileId)
    let secret: string | undefined
    if (profile.backend === 'session') secret = this.sessions.get(profile.id)
    if (profile.backend === 'portable-vault') secret = this.unlockedVaults.get(profile.id)
    if (profile.backend === 'env' && profile.envFilePath) secret = parseEnv(profile.envFilePath).get(profile.environmentVariable)
    if (profile.backend === 'os' && profile.payloadPath) {
      if (!await safeStorage.isAsyncEncryptionAvailable()) throw new Error('OS-backed credential provider is unavailable.')
      if (process.platform === 'linux' && safeStorage.getSelectedStorageBackend() === 'basic_text') throw new Error('Refusing to decrypt through Linux basic_text backend.')
      const result = await safeStorage.decryptStringAsync(readFileSync(profile.payloadPath))
      secret = result.result
      if (result.shouldReEncrypt) {
        const encrypted = await safeStorage.encryptStringAsync(secret)
        writeFileSync(profile.payloadPath, encrypted, { mode: 0o600 })
      }
    }
    if (!secret) throw new Error(`Credential profile ${profile.name} is locked or unavailable.`)
    return { [profile.environmentVariable]: secret }
  }

  private summary(profile: SecretProfileRecord): SecretProfileSummary {
    const backend = process.platform === 'linux' && profile.backend === 'os' ? safeStorage.getSelectedStorageBackend() : undefined
    const unlocked = profile.backend === 'env' || profile.backend === 'os' || this.sessions.has(profile.id) || this.unlockedVaults.has(profile.id)
    return {
      id: profile.id,
      name: profile.name,
      provider: profile.provider,
      environmentVariable: profile.environmentVariable,
      backend: profile.backend,
      envFilePath: profile.envFilePath,
      createdAt: profile.createdAt,
      updatedAt: profile.updatedAt,
      unlocked,
      persistent: profile.backend !== 'session',
      secure: profile.backend === 'portable-vault' || profile.backend === 'os' && backend !== 'basic_text',
      warning: profile.backend === 'env' ? 'Plaintext file-backed expert mode.' : backend === 'basic_text' ? 'Linux basic_text is not accepted as secure persistence.' : undefined,
    }
  }

  private readIndex(): SecretIndex {
    try {
      const parsed = JSON.parse(readFileSync(this.indexPath, 'utf8')) as SecretIndex
      return parsed.schemaVersion === 1 && Array.isArray(parsed.profiles) ? parsed : { schemaVersion: 1, profiles: [] }
    } catch { return { schemaVersion: 1, profiles: [] } }
  }

  private requireProfile(id: string): SecretProfileRecord {
    const profile = this.readIndex().profiles.find((item) => item.id === id)
    if (!profile) throw new Error('Credential profile not found.')
    return profile
  }
}
