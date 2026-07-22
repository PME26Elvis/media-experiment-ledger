import { createHash } from 'node:crypto'
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import { CustomModelManager } from '../src/main/custom-model-manager'
import { parseUserModelManifest } from '../src/shared/custom-model-schema'

const roots: string[] = []
function root(): string {
  const path = mkdtempSync(join(tmpdir(), 'mel-custom-model-'))
  roots.push(path)
  return path
}
function digest(value: Buffer): string {
  return createHash('sha256').update(value).digest('hex')
}
afterEach(() => {
  for (const path of roots.splice(0)) rmSync(path, { recursive: true, force: true })
})

describe('declarative custom model manifests', () => {
  it('imports only an adjacent hash-pinned ONNX artifact and lists it as user-supplied', () => {
    const userData = root()
    const source = root()
    const model = Buffer.from('synthetic-onnx-fixture')
    writeFileSync(join(source, 'model.onnx'), model)
    const manifest = {
      schemaVersion: 1,
      displayName: 'User YOLOX',
      family: 'YOLOX',
      variant: 'Lab-S',
      adapter: 'yolox-v1',
      inputWidth: 640,
      inputHeight: 640,
      labels: 'coco-80',
      modelFile: 'model.onnx',
      modelSha256: digest(model),
      licenseNote: 'User confirms local use rights.',
    }
    const manifestPath = join(source, 'manifest.json')
    writeFileSync(manifestPath, JSON.stringify(manifest), 'utf8')
    const manager = new CustomModelManager(userData)
    const record = manager.import(manifestPath)
    expect(record.id).toMatch(/^user-yolox-/u)
    expect(record.distributionMode).toBe('user-supplied')
    expect(record.licenseState).toBe('user-supplied-only')
    expect(readFileSync(record.localPath!)).toEqual(model)
    expect(manager.list()).toEqual([expect.objectContaining({ id: record.id, installed: true })])
    expect(manager.remove(record.id)).toBe(true)
    expect(manager.list()).toEqual([])
  })

  it('rejects mismatched adapters, executable paths and hash changes', () => {
    expect(() => parseUserModelManifest({
      schemaVersion: 1, displayName: 'Bad', family: 'YOLOX', variant: 'x', adapter: 'nanodet-plus-v1',
      inputWidth: 320, inputHeight: 320, labels: 'coco-80', modelFile: '../model.onnx', modelSha256: '0'.repeat(64), licenseNote: 'x',
    })).toThrow()

    const userData = root()
    const source = root()
    writeFileSync(join(source, 'model.onnx'), 'changed')
    const manifestPath = join(source, 'manifest.json')
    writeFileSync(manifestPath, JSON.stringify({
      schemaVersion: 1, displayName: 'Pinned', family: 'NanoDet-Plus', variant: 'm-test', adapter: 'nanodet-plus-v1',
      inputWidth: 320, inputHeight: 320, labels: 'coco-80', modelFile: 'model.onnx', modelSha256: '0'.repeat(64), licenseNote: 'local',
    }), 'utf8')
    expect(() => new CustomModelManager(userData).import(manifestPath)).toThrow(/SHA-256 mismatch/u)
  })
})
