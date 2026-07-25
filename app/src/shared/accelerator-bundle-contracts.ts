export type AcceleratorBundleProfile = 'directml' | 'cuda' | 'coreml'
export type AcceleratorBundleState = 'installed' | 'active' | 'quarantined'

export interface AcceleratorBundleFile {
  path: string
  sizeBytes: number
  sha256: string
  kind: 'engine' | 'native' | 'metadata' | 'license' | 'sbom'
}

export interface AcceleratorRuntimeRequirements {
  minimumOsVersion?: string
  minimumNvidiaDriver?: string
  cudaMajor?: number
  cudnnMajor?: number
}

export interface AcceleratorBundleManifest {
  schemaVersion: 1
  bundleId: string
  version: string
  profile: AcceleratorBundleProfile
  platform: NodeJS.Platform
  arch: string
  appVersion: { minimum: string; maximum?: string }
  engine: {
    entrypoint: string
    sha256: string
    onnxRuntimeVersion: string
    requiredProviders: string[]
    distributions: Record<string, string>
  }
  runtimeRequirements: AcceleratorRuntimeRequirements
  files: AcceleratorBundleFile[]
  sbomFile: string
  noticesFile: string
  nativeInventoryFile: string
  signedPayload: string
  signature: string
}

export interface AcceleratorBundleVerification {
  schemaVersion: 1
  verifiedAt: string
  manifestSha256: string
  signatureVerified: boolean
  filesVerified: number
  providerSelfTestPassed: boolean
  providerInventory?: Record<string, unknown>
  warnings: string[]
}

export interface AcceleratorBundleRecord {
  bundleId: string
  version: string
  profile: AcceleratorBundleProfile
  platform: string
  arch: string
  state: AcceleratorBundleState
  installedAt: string
  activatedAt?: string
  path: string
  manifest: AcceleratorBundleManifest
  verification?: AcceleratorBundleVerification
  quarantineReason?: string
}

export interface AcceleratorBundleSnapshot {
  schemaVersion: 1
  capturedAt: string
  trustKeyPath?: string
  active?: { bundleId: string; version: string; profile: AcceleratorBundleProfile; activatedAt: string }
  installed: AcceleratorBundleRecord[]
  quarantined: AcceleratorBundleRecord[]
  host: {
    platform: NodeJS.Platform
    arch: string
    appVersion: string
    osVersion: string
    nvidiaDriver?: string
  }
  warnings: string[]
}

export const ACCELERATOR_BUNDLE_IPC = {
  snapshot: 'mel:accelerator-bundles-snapshot',
  install: 'mel:accelerator-bundles-install',
  activate: 'mel:accelerator-bundles-activate',
  rollback: 'mel:accelerator-bundles-rollback',
  quarantine: 'mel:accelerator-bundles-quarantine',
  remove: 'mel:accelerator-bundles-remove',
} as const

export interface AcceleratorBundleApi {
  snapshot(refresh?: boolean): Promise<AcceleratorBundleSnapshot>
  install(manifestPath: string): Promise<AcceleratorBundleRecord>
  activate(bundleId: string, version: string): Promise<AcceleratorBundleSnapshot>
  rollback(): Promise<AcceleratorBundleSnapshot>
  quarantine(bundleId: string, version: string, reason: string): Promise<AcceleratorBundleSnapshot>
  remove(bundleId: string, version: string): Promise<AcceleratorBundleSnapshot>
}
