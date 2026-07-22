import { createHash } from 'node:crypto'
import { createReadStream, mkdirSync, copyFileSync, rmSync, statSync } from 'node:fs'
import { basename, extname, join } from 'node:path'
import type { ModelRecord } from '../shared/contracts'
import { MODEL_REGISTRY, registryModel } from '../shared/model-registry'
import { StudioDatabase } from './database'

async function hashFile(path: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const hash = createHash('sha256')
    const stream = createReadStream(path)
    stream.on('data', (chunk) => hash.update(chunk))
    stream.on('error', reject)
    stream.on('end', () => resolve(hash.digest('hex')))
  })
}

export class ModelManager {
  private readonly root: string
  constructor(private readonly db: StudioDatabase, userDataPath: string) {
    this.root = join(userDataPath, 'models')
    mkdirSync(this.root, { recursive: true })
  }

  list(): ModelRecord[] {
    const installed = new Map(this.db.listModelInstallations().map((item) => [item.modelId, item]))
    return MODEL_REGISTRY.map((model) => {
      const entry = installed.get(model.id)
      return { ...model, installed: Boolean(entry), localPath: entry?.localPath, sha256: entry?.sha256, sizeBytes: entry?.sizeBytes, importedAt: entry?.importedAt }
    })
  }

  async import(modelId: string, sourcePath: string): Promise<ModelRecord> {
    const model = registryModel(modelId)
    if (extname(sourcePath).toLowerCase() !== '.onnx') throw new Error('Only ONNX model artifacts are accepted.')
    const source = statSync(sourcePath)
    if (!source.isFile() || source.size < 1024) throw new Error('Model artifact is missing or unexpectedly small.')
    const digest = await hashFile(sourcePath)
    const destination = join(this.root, `${model.id}-${digest.slice(0, 12)}-${basename(sourcePath)}`)
    copyFileSync(sourcePath, destination)
    const importedAt = new Date().toISOString()
    this.db.upsertModelInstallation({ modelId, localPath: destination, sha256: digest, sizeBytes: source.size, importedAt })
    return this.list().find((item) => item.id === modelId)!
  }

  remove(modelId: string): boolean {
    const installation = this.db.getModelInstallation(modelId)
    if (!installation) return false
    rmSync(installation.localPath, { force: true })
    this.db.removeModelInstallation(modelId)
    return true
  }
}
