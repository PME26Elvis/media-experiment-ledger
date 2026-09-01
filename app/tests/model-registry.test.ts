import { describe, expect, it } from 'vitest'
import { MODEL_REGISTRY, registryModel } from '../src/shared/model-registry'
describe('model registry',()=>{ it('contains unique stable IDs and explicit rights state',()=>{expect(new Set(MODEL_REGISTRY.map(model=>model.id)).size).toBe(MODEL_REGISTRY.length); expect(MODEL_REGISTRY.every(model=>model.licenseState&&model.distributionMode)).toBe(true)}); it('resolves supported adapters and rejects unknown IDs',()=>{expect(registryModel('yolox-tiny-coco-416').adapter).toBe('yolox-coco-v1'); expect(()=>registryModel('unknown')).toThrow()}) })
