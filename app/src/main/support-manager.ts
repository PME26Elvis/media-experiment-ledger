import { app } from 'electron'
import { createHash, randomUUID } from 'node:crypto'
import {
  existsSync,
  mkdirSync,
  readFileSync,
  renameSync,
  statSync,
  writeFileSync,
} from 'node:fs'
import { gzipSync } from 'node:zlib'
import { basename, dirname, join, resolve } from 'node:path'
import type {
  DiagnosticsPayload,
  SupportBundleResult,
  TelemetryConsent,
  TelemetrySendResult,
} from '../shared/diagnostics-contracts'
import { containsSecretLikeValue, redactText } from '../shared/diagnostics'
import type { StudioDatabase } from './database'

const CONSENT_FILE = 'telemetry-consent.json'

function sha256(value: Buffer): string {
  return createHash('sha256').update(value).digest('hex')
}

function atomicJson(path: string, value: unknown): void {
  mkdirSync(dirname(path), { recursive: true })
  const temporary = `${path}.${randomUUID()}.tmp`
  writeFileSync(temporary, JSON.stringify(value, null, 2), 'utf8')
  renameSync(temporary, path)
}

function safeOutputDirectory(path: string): string {
  const resolved = resolve(path)
  if (!resolved || basename(resolved) === '.') throw new Error('A diagnostics output directory is required.')
  mkdirSync(resolved, { recursive: true })
  return resolved
}

export class SupportManager {
  private readonly consentPath: string

  constructor(
    private readonly userDataPath: string,
    private readonly database: StudioDatabase,
  ) {
    this.consentPath = join(userDataPath, CONSENT_FILE)
  }

  consent(): TelemetryConsent {
    try {
      const value = JSON.parse(readFileSync(this.consentPath, 'utf8')) as Partial<TelemetryConsent>
      return {
        schemaVersion: 1,
        enabled: value.enabled === true,
        endpoint: typeof value.endpoint === 'string' ? value.endpoint : '',
        updatedAt: typeof value.updatedAt === 'string' ? value.updatedAt : new Date(0).toISOString(),
      }
    } catch {
      return {
        schemaVersion: 1,
        enabled: false,
        endpoint: '',
        updatedAt: new Date(0).toISOString(),
      }
    }
  }

  setConsent(enabled: boolean, endpoint: string): TelemetryConsent {
    const normalized = endpoint.trim()
    if (enabled) {
      const url = new URL(normalized)
      if (url.protocol !== 'https:') throw new Error('Remote diagnostics require an HTTPS endpoint.')
      if (url.username || url.password) throw new Error('Telemetry endpoint URLs cannot contain credentials.')
      url.search = ''
      url.hash = ''
      endpoint = url.toString()
    } else {
      endpoint = normalized
    }
    const value: TelemetryConsent = {
      schemaVersion: 1,
      enabled,
      endpoint,
      updatedAt: new Date().toISOString(),
    }
    atomicJson(this.consentPath, value)
    return value
  }

  preview(): DiagnosticsPayload {
    const integrity = this.database.integrityCheck()
    const engine = this.engineSummary()
    const jobs = this.database.listJobs().slice(0, 250).map(job => ({
      kind: job.kind,
      status: job.status,
      stage: redactText(job.stage),
      progress: Math.round(job.progress * 1000) / 1000,
      completedItems: job.completedItems,
      totalItems: job.totalItems,
      error: job.error ? redactText(job.error) : undefined,
      updatedAt: job.updatedAt,
    }))
    const payload: DiagnosticsPayload = {
      schemaVersion: 1,
      generatedAt: new Date().toISOString(),
      app: {
        version: app.getVersion(),
        packaged: app.isPackaged,
        platform: process.platform,
        arch: process.arch,
        electron: process.versions.electron,
        node: process.versions.node,
      },
      database: integrity,
      engine,
      jobs,
      redaction: {
        version: 1,
        rawPathsIncluded: false,
        secretsIncluded: false,
        jobConfigsIncluded: false,
        mediaIncluded: false,
      },
    }
    if (containsSecretLikeValue(payload)) {
      throw new Error('Diagnostics payload failed the secret/path redaction gate.')
    }
    return payload
  }

  createBundle(outputDirectory: string): SupportBundleResult {
    const payload = this.preview()
    const root = safeOutputDirectory(outputDirectory)
    const timestamp = new Date().toISOString().replace(/[:.]/gu, '-')
    const json = Buffer.from(JSON.stringify(payload, null, 2), 'utf8')
    const compressed = gzipSync(json, { level: 9 })
    const bundlePath = join(root, `mel-support-${timestamp}.json.gz`)
    const temporary = `${bundlePath}.tmp`
    writeFileSync(temporary, compressed)
    renameSync(temporary, bundlePath)
    const digest = sha256(compressed)
    const manifestPath = `${bundlePath}.manifest.json`
    atomicJson(manifestPath, {
      schemaVersion: 1,
      bundleFile: basename(bundlePath),
      bundleSha256: digest,
      bundleSizeBytes: compressed.length,
      uncompressedBytes: json.length,
      redactionVersion: 1,
      createdAt: payload.generatedAt,
    })
    return {
      bundlePath,
      manifestPath,
      sha256: digest,
      sizeBytes: compressed.length,
      uncompressedBytes: json.length,
    }
  }

  async send(): Promise<TelemetrySendResult> {
    const consent = this.consent()
    if (!consent.enabled) throw new Error('Remote diagnostics are disabled. Review and opt in first.')
    const endpoint = new URL(consent.endpoint)
    if (endpoint.protocol !== 'https:') throw new Error('Remote diagnostics require HTTPS.')
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 15_000)
    timeout.unref()
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        redirect: 'error',
        headers: {
          'content-type': 'application/json',
          'user-agent': `MEL-Studio/${app.getVersion()}`,
        },
        body: JSON.stringify(this.preview()),
        signal: controller.signal,
      })
      if (!response.ok) throw new Error(`Diagnostics endpoint returned HTTP ${response.status}.`)
      return {
        sent: true,
        status: response.status,
        receivedAt: new Date().toISOString(),
      }
    } finally {
      clearTimeout(timeout)
    }
  }

  private engineSummary(): DiagnosticsPayload['engine'] {
    const candidates = [
      join(process.resourcesPath, 'engine-bin', 'mel-engine', 'engine-build-manifest.json'),
      join(__dirname, '../../../engine-bin/mel-engine/engine-build-manifest.json'),
    ]
    const path = candidates.find(candidate => existsSync(candidate) && statSync(candidate).isFile())
    if (!path) return { available: false }
    try {
      const value = JSON.parse(readFileSync(path, 'utf8')) as Record<string, unknown>
      return {
        available: true,
        version: typeof value.engine_version === 'string' ? value.engine_version : undefined,
        platform: typeof value.platform === 'string' ? value.platform : undefined,
        machine: typeof value.machine === 'string' ? value.machine : undefined,
        fileCount: typeof value.file_count === 'number' ? value.file_count : undefined,
        totalBytes: typeof value.total_bytes === 'number' ? value.total_bytes : undefined,
        capabilities: Array.isArray(value.capabilities)
          ? value.capabilities.filter(item => typeof item === 'string').slice(0, 100) as string[]
          : undefined,
      }
    } catch {
      return { available: false }
    }
  }
}
