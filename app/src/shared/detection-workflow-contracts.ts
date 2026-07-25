import type { HardwareProviderKey } from './hardware-contracts'

export const DETECTION_WORKFLOW_IPC = {
  browse: 'mel:detection-browse',
  presetsList: 'mel:detection-presets-list',
  presetsSave: 'mel:detection-presets-save',
  presetsRemove: 'mel:detection-presets-remove',
  presetsSetDefault: 'mel:detection-presets-set-default',
} as const

export interface DetectionPreset {
  id: string
  name: string
  modelId: string
  provider: HardwareProviderKey
  benchmarkModelIds: string[]
  benchmarkProviders: HardwareProviderKey[]
  deviceId: number
  coremlComputeUnits: 'ALL' | 'CPU_ONLY' | 'CPU_AND_GPU' | 'CPU_AND_NE'
  allowCpuFallback: boolean
  scoreThreshold: number
  nmsIouThreshold: number
  maxDetections: number
  sampleEveryNFrames: number
  sampleTargetFps: number
  maxSampledFrames: number
  exportAnnotatedVideo: boolean
  exportCrops: boolean
  benchmarkSampleCount: number
  warmIterations: number
  createdAt: string
  updatedAt: string
}

export interface DetectionPresetSnapshot {
  schemaVersion: 1
  defaultPresetId?: string
  presets: DetectionPreset[]
}

export interface DetectionBrowserRequest {
  manifestPath: string
  query?: string
  className?: string
  minConfidence?: number
  page?: number
  pageSize?: number
}

export interface DetectionBrowserDetection {
  classId: number
  className: string
  confidence: number
  bboxXyxy: number[]
  areaPixels: number
  areaFraction: number
  cropPath?: string
}

export interface DetectionBrowserItem {
  itemId: string
  sourcePath: string
  sourceType: 'image' | 'video-frame'
  sourceWidth: number
  sourceHeight: number
  frameIndex?: number
  timestampSeconds?: number
  detectionCount: number
  classes: string[]
  annotatedPath?: string
  detections: DetectionBrowserDetection[]
}

export interface DetectionBrowserResult {
  schemaVersion: 1
  manifestPath: string
  modelId?: string
  requestedProvider?: string
  sampledItemCount: number
  boxCount: number
  classNames: string[]
  exports: Record<string, unknown>
  page: number
  pageSize: number
  totalItems: number
  items: DetectionBrowserItem[]
}

export interface DetectionWorkflowApi {
  browse(request: DetectionBrowserRequest): Promise<DetectionBrowserResult>
  presets: {
    list(): Promise<DetectionPresetSnapshot>
    save(preset: Omit<DetectionPreset, 'id' | 'createdAt' | 'updatedAt'> & { id?: string }): Promise<DetectionPresetSnapshot>
    remove(id: string): Promise<DetectionPresetSnapshot>
    setDefault(id?: string): Promise<DetectionPresetSnapshot>
  }
}
