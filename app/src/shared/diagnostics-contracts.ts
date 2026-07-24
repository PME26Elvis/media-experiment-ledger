export const DIAGNOSTICS_IPC = {
  preview: 'mel:diagnostics-preview',
  createBundle: 'mel:diagnostics-create-bundle',
  consentGet: 'mel:telemetry-consent-get',
  consentSet: 'mel:telemetry-consent-set',
  send: 'mel:telemetry-send',
} as const

export interface TelemetryConsent {
  schemaVersion: 1
  enabled: boolean
  endpoint: string
  updatedAt: string
}

export interface DiagnosticsJobSummary {
  kind: string
  status: string
  stage: string
  progress: number
  completedItems: number
  totalItems: number
  error?: string
  updatedAt: string
}

export interface DiagnosticsPayload {
  schemaVersion: 1
  generatedAt: string
  app: {
    version: string
    packaged: boolean
    platform: string
    arch: string
    electron: string
    node: string
  }
  database: {
    ok: boolean
    schemaVersion: number
    messages: string[]
  }
  engine: {
    available: boolean
    version?: string
    platform?: string
    machine?: string
    fileCount?: number
    totalBytes?: number
    capabilities?: string[]
  }
  jobs: DiagnosticsJobSummary[]
  redaction: {
    version: 1
    rawPathsIncluded: false
    secretsIncluded: false
    jobConfigsIncluded: false
    mediaIncluded: false
  }
}

export interface SupportBundleResult {
  bundlePath: string
  manifestPath: string
  sha256: string
  sizeBytes: number
  uncompressedBytes: number
}

export interface TelemetrySendResult {
  sent: boolean
  status: number
  receivedAt: string
}

export interface DiagnosticsApi {
  preview(): Promise<DiagnosticsPayload>
  createBundle(outputDirectory: string): Promise<SupportBundleResult>
  consent: {
    get(): Promise<TelemetryConsent>
    set(enabled: boolean, endpoint: string): Promise<TelemetryConsent>
  }
  send(): Promise<TelemetrySendResult>
}
