import type { ModelRecord } from './contracts'

type RegistryModel = Omit<ModelRecord, 'installed' | 'localPath' | 'sha256' | 'sizeBytes' | 'importedAt'>

export const MODEL_REGISTRY: readonly RegistryModel[] = [
  { id: 'yolox-tiny-coco-416', family: 'YOLOX', variant: 'Tiny', inputWidth: 416, inputHeight: 416, adapter: 'yolox-coco-v1', labels: 'coco-80-v1', computeTier: 'light', distributionMode: 'user-supplied', licenseState: 'needs-review', sourceUrl: 'https://github.com/Megvii-BaseDetection/YOLOX' },
  { id: 'yolox-s-coco-640', family: 'YOLOX', variant: 'S', inputWidth: 640, inputHeight: 640, adapter: 'yolox-coco-v1', labels: 'coco-80-v1', computeTier: 'medium', distributionMode: 'user-supplied', licenseState: 'needs-review', sourceUrl: 'https://github.com/Megvii-BaseDetection/YOLOX' },
  { id: 'yolox-l-coco-640', family: 'YOLOX', variant: 'L', inputWidth: 640, inputHeight: 640, adapter: 'yolox-coco-v1', labels: 'coco-80-v1', computeTier: 'heavy', distributionMode: 'user-supplied', licenseState: 'needs-review', sourceUrl: 'https://github.com/Megvii-BaseDetection/YOLOX' },
  { id: 'nanodet-plus-m-320-coco', family: 'NanoDet-Plus', variant: 'm-320', inputWidth: 320, inputHeight: 320, adapter: 'nanodet-plus-coco-v1', labels: 'coco-80-v1', computeTier: 'light', distributionMode: 'user-supplied', licenseState: 'needs-review', sourceUrl: 'https://github.com/RangiLyu/nanodet' },
  { id: 'nanodet-plus-m-416-coco', family: 'NanoDet-Plus', variant: 'm-416', inputWidth: 416, inputHeight: 416, adapter: 'nanodet-plus-coco-v1', labels: 'coco-80-v1', computeTier: 'medium', distributionMode: 'user-supplied', licenseState: 'needs-review', sourceUrl: 'https://github.com/RangiLyu/nanodet' },
  { id: 'nanodet-plus-m-1.5x-416-coco', family: 'NanoDet-Plus', variant: 'm-1.5x-416', inputWidth: 416, inputHeight: 416, adapter: 'nanodet-plus-coco-v1', labels: 'coco-80-v1', computeTier: 'heavy', distributionMode: 'user-supplied', licenseState: 'needs-review', sourceUrl: 'https://github.com/RangiLyu/nanodet' },
] as const

export function registryModel(id: string): RegistryModel {
  const model = MODEL_REGISTRY.find((item) => item.id === id)
  if (!model) throw new Error(`Unknown model registry id: ${id}`)
  return model
}
