import { createHash, randomUUID } from 'node:crypto'
import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, renameSync, rmSync, statSync, writeFileSync } from 'node:fs'
import { basename, dirname, join, resolve, sep } from 'node:path'
import type { ModelRecord } from '../shared/contracts'
import type { UserModelManifest } from '../shared/custom-model-contracts'
import { parseUserModelManifest } from '../shared/custom-model-schema'

interface StoredCustomModel {
  schemaVersion: 1
  manifest: UserModelManifest
  record: ModelRecord
  importedAt: string
}

function sha256(path: string): string {
  const digest = createHash('sha256')
  digest.update(readFileSync(path))
  return digest.digest('hex')
}

function atomicJson(path: string, value: unknown): void {
  mkdirSync(dirname(path), { recursive: true })
  const temporary = `${path}.${randomUUID()}.tmp`
  writeFileSync(temporary, JSON.stringify(value, null, 2), 'utf8')
  renameSync(temporary, path)
}

function tier(sizeBytes: number, width: number, height: number): ModelRecord['computeTier'] {
  const score = sizeBytes * (width * height / (320 * 320))
  if (score < 20_000_000) return 'light'
  if (score < 150_000_000) return 'medium'
  return 'heavy'
}

function safeId(value: string): string {
  if (!/^user-(?:yolox|nanodet)-[0-9a-f]{16}$/u.test(value)) throw new Error('Invalid custom model ID.')
  return value
}

function runtimeAdapter(manifest: UserModelManifest): ModelRecord['adapter'] {
  return manifest.adapter === 'yolox-v1' ? 'yolox-coco-v1' : 'nanodet-plus-coco-v1'
}

export class CustomModelManager {
  private readonly root: string

  constructor(userDataPath: string) {
    this.root = join(userDataPath, 'models', 'user-supplied')
    mkdirSync(this.root, { recursive: true })
  }

  list(): ModelRecord[] {
    return readdirSync(this.root, { withFileTypes: true })
      .filter(entry => entry.isDirectory())
      .flatMap(entry => {
        try {
          const value = JSON.parse(readFileSync(join(this.root, entry.name, 'record.json'), 'utf8')) as StoredCustomModel
          const modelPath = String(value.record.localPath ?? '')
          if (value.schemaVersion !== 1 || !modelPath || !existsSync(modelPath)) return []
          if (sha256(modelPath) !== value.record.sha256) return []
          return [{ ...value.record, installed: true }]
        } catch {
          return []
        }
      })
      .sort((a, b) => `${a.family}-${a.variant}`.localeCompare(`${b.family}-${b.variant}`))
  }

  import(manifestPath: string): ModelRecord {
    const resolvedManifest = resolve(manifestPath)
    const manifest = parseUserModelManifest(JSON.parse(readFileSync(resolvedManifest, 'utf8')))
    const modelSource = resolve(dirname(resolvedManifest), manifest.modelFile)
    if (!modelSource.startsWith(`${resolve(dirname(resolvedManifest))}${sep}`) || basename(modelSource) !== manifest.modelFile) {
      throw new Error('Custom model artifact must be adjacent to its manifest.')
    }
    if (!existsSync(modelSource) || !statSync(modelSource).isFile()) throw new Error(`Custom ONNX artifact not found: ${manifest.modelFile}`)
    const actualSha = sha256(modelSource)
    if (actualSha !== manifest.modelSha256.toLowerCase()) throw new Error(`Custom model SHA-256 mismatch: expected ${manifest.modelSha256}, got ${actualSha}`)
    const prefix = manifest.family === 'YOLOX' ? 'yolox' : 'nanodet'
    const id = `user-${prefix}-${actualSha.slice(0, 16)}`
    const destinationRoot = join(this.root, id)
    mkdirSync(destinationRoot, { recursive: true })
    const destination = join(destinationRoot, 'model.onnx')
    const temporary = `${destination}.${randomUUID()}.partial`
    copyFileSync(modelSource, temporary)
    if (sha256(temporary) !== actualSha) {
      rmSync(temporary, { force: true })
      throw new Error('Custom model changed while being imported.')
    }
    renameSync(temporary, destination)
    const importedAt = new Date().toISOString()
    const record: ModelRecord = {
      id,
      family: manifest.family,
      variant: manifest.variant,
      inputWidth: manifest.inputWidth,
      inputHeight: manifest.inputHeight,
      adapter: runtimeAdapter(manifest),
      labels: 'coco-80-v1',
      computeTier: tier(statSync(destination).size, manifest.inputWidth, manifest.inputHeight),
      distributionMode: 'user-supplied',
      licenseState: 'user-supplied-only',
      installed: true,
      localPath: destination,
      sha256: actualSha,
      sizeBytes: statSync(destination).size,
      importedAt,
    }
    atomicJson(join(destinationRoot, 'record.json'), { schemaVersion: 1, manifest, record, importedAt } satisfies StoredCustomModel)
    return record
  }

  remove(modelId: string): boolean {
    const path = resolve(this.root, safeId(modelId))
    const root = resolve(this.root)
    if (!path.startsWith(`${root}${sep}`) || !existsSync(path)) return false
    rmSync(path, { recursive: true, force: true })
    return true
  }
}
