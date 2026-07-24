import type { CreateJobRequest } from './contracts'

export const INTEGRATION_IPC = {
  schedulesList: 'mel:integrations-schedules-list',
  schedulesSave: 'mel:integrations-schedules-save',
  schedulesRemove: 'mel:integrations-schedules-remove',
  schedulesRunNow: 'mel:integrations-schedules-run-now',
  schedulesPreview: 'mel:integrations-schedules-preview',
  syncRun: 'mel:integrations-sync-run',
  githubPublish: 'mel:integrations-github-publish',
  wasmPostprocess: 'mel:integrations-wasm-postprocess',
} as const

export type ScheduleCadence =
  | { kind: 'daily'; hour: number; minute: number }
  | { kind: 'weekly'; weekdays: number[]; hour: number; minute: number }
  | { kind: 'interval'; hours: number }

export interface SaveScheduleRequest {
  id?: string
  name: string
  enabled: boolean
  cadence: ScheduleCadence
  job: CreateJobRequest
}

export interface ScheduledJobDefinition extends SaveScheduleRequest {
  id: string
  backend: 'task-scheduler' | 'launch-agent' | 'systemd-user'
  createdAt: string
  updatedAt: string
}

export interface SchedulerPreview {
  backend: ScheduledJobDefinition['backend']
  files: Array<{ path: string; content: string }>
  commands: string[][]
}

export interface CloudSyncRequest {
  projectRoot: string
  syncRoot: string
  dryRun?: boolean
}

export interface CloudSyncConflict {
  path: string
  baseSha256?: string
  localSha256?: string
  remoteSha256?: string
  resolution: 'local-preserved'
  remoteCopyPath?: string
}

export interface CloudSyncResult {
  snapshotId: string
  direction: 'initialized' | 'uploaded' | 'downloaded' | 'merged' | 'noop'
  uploadedFiles: number
  downloadedFiles: number
  deletedFiles: number
  conflicts: CloudSyncConflict[]
  projectStatePath: string
  remoteHeadPath: string
}

export interface GitHubPublishRequest {
  repository: string
  tag: string
  name: string
  body: string
  draft: boolean
  prerelease: boolean
  assetPaths: string[]
  credentialProfileId: string
}

export interface GitHubPublishResult {
  releaseId: number
  htmlUrl: string
  tag: string
  uploadedAssets: Array<{ name: string; sizeBytes: number }>
  draft: boolean
  prerelease: boolean
}

export interface WasmPostprocessRequest {
  modulePath: string
  sha256: string
  input: unknown
  timeoutMs?: number
  maxMemoryPages?: number
}

export interface WasmPostprocessResult {
  output: unknown
  durationMs: number
  memoryPages: number
  moduleSha256: string
}

export interface IntegrationApi {
  schedules: {
    list(): Promise<ScheduledJobDefinition[]>
    save(request: SaveScheduleRequest): Promise<ScheduledJobDefinition>
    remove(id: string): Promise<boolean>
    runNow(id: string): Promise<unknown>
    preview(request: SaveScheduleRequest): Promise<SchedulerPreview>
  }
  sync: {
    run(request: CloudSyncRequest): Promise<CloudSyncResult>
  }
  github: {
    publish(request: GitHubPublishRequest): Promise<GitHubPublishResult>
  }
  wasm: {
    postprocess(request: WasmPostprocessRequest): Promise<WasmPostprocessResult>
  }
}
