export const IPC = {
  systemInfo: 'mel:system-info',
  chooseDirectory: 'mel:choose-directory',
  chooseFile: 'mel:choose-file',
  revealPath: 'mel:reveal-path',
  settingsGet: 'mel:settings-get',
  settingsSet: 'mel:settings-set',
  jobsList: 'mel:jobs-list',
  jobsCreate: 'mel:jobs-create',
  jobsControl: 'mel:jobs-control',
  modelsList: 'mel:models-list',
  modelsImport: 'mel:models-import',
  modelsRemove: 'mel:models-remove',
  updaterCheck: 'mel:updater-check',
  updaterInstall: 'mel:updater-install',
} as const

export type JobKind = 'scan' | 'atlas' | 'detection' | 'automation' | 'pdf-export' | 'sample-download'
export type JobStatus = 'queued' | 'running' | 'pausing' | 'paused' | 'cancelling' | 'cancelled' | 'failed' | 'recoverable' | 'completed'

export interface JobRecord {
  id: string
  kind: JobKind
  title: string
  status: JobStatus
  stage: string
  progress: number
  completedItems: number
  totalItems: number
  config: Record<string, unknown>
  output?: Record<string, unknown>
  error?: string
  createdAt: string
  updatedAt: string
}

export interface CreateJobRequest {
  kind: JobKind
  title: string
  config: Record<string, unknown>
}

export type ModelLicenseState = 'verified' | 'needs-review' | 'user-supplied-only' | 'blocked'
export type ModelDistributionMode = 'bundled' | 'download' | 'user-supplied' | 'blocked'

export interface ModelRecord {
  id: string
  family: 'YOLOX' | 'NanoDet-Plus'
  variant: string
  inputWidth: number
  inputHeight: number
  adapter: string
  labels: string
  computeTier: 'light' | 'medium' | 'heavy'
  distributionMode: ModelDistributionMode
  licenseState: ModelLicenseState
  sourceUrl?: string
  installed: boolean
  localPath?: string
  sha256?: string
  sizeBytes?: number
  importedAt?: string
}

export interface SystemInfo {
  platform: NodeJS.Platform
  arch: string
  version: string
  appDataPath: string
  documentsPath: string
  downloadsPath: string
  engineReady: boolean
}

export interface StudioSettings {
  locale: 'zh-TW' | 'en' | 'zh-CN' | 'ja' | 'ko'
  appearance: 'system' | 'light' | 'dark'
  imageInputPath: string
  videoInputPath: string
  atlasOutputPath: string
  detectionOutputPath: string
  generatedOutputPath: string
  closeBehavior: 'ask' | 'tray' | 'quit'
  reducedMotion: boolean
}

export interface MelDesktopApi {
  systemInfo(): Promise<SystemInfo>
  chooseDirectory(defaultPath?: string): Promise<string | null>
  chooseFile(options?: { title?: string; extensions?: string[] }): Promise<string | null>
  revealPath(path: string): Promise<boolean>
  settings: {
    get(): Promise<StudioSettings>
    set(patch: Partial<StudioSettings>): Promise<StudioSettings>
  }
  jobs: {
    list(): Promise<JobRecord[]>
    create(request: CreateJobRequest): Promise<JobRecord>
    control(id: string, action: 'pause' | 'resume' | 'cancel'): Promise<JobRecord>
  }
  models: {
    list(): Promise<ModelRecord[]>
    import(modelId: string, sourcePath: string): Promise<ModelRecord>
    remove(modelId: string): Promise<boolean>
  }
  updater: {
    check(): Promise<{ status: string; version?: string; error?: string }>
    install(): Promise<boolean>
  }
}
