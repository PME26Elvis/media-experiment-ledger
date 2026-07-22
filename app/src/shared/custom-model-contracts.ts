import type { ModelRecord } from './contracts'

export const CUSTOM_MODEL_IPC = {
  import: 'mel:custom-model-import',
  remove: 'mel:custom-model-remove',
} as const

export interface UserModelManifest {
  schemaVersion: 1
  displayName: string
  family: 'YOLOX' | 'NanoDet-Plus'
  variant: string
  adapter: 'yolox-v1' | 'nanodet-plus-v1'
  inputWidth: number
  inputHeight: number
  labels: 'coco-80'
  modelFile: string
  modelSha256: string
  licenseNote: string
}

export interface CustomModelApi {
  import(manifestPath: string): Promise<ModelRecord>
  remove(modelId: string): Promise<boolean>
}
