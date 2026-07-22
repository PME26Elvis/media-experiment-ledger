import { DatabaseSync } from 'node:sqlite'
import { mkdirSync } from 'node:fs'
import { dirname } from 'node:path'
import type { JobRecord, StudioSettings } from '../shared/contracts'

const defaults: StudioSettings = {
  locale: 'zh-TW', appearance: 'system', imageInputPath: '', videoInputPath: '', atlasOutputPath: '', detectionOutputPath: '', generatedOutputPath: '', closeBehavior: 'ask', reducedMotion: false,
}

export interface ModelInstallation {
  modelId: string
  localPath: string
  sha256: string
  sizeBytes: number
  importedAt: string
}

export class StudioDatabase {
  private readonly db: DatabaseSync

  constructor(path: string) {
    mkdirSync(dirname(path), { recursive: true })
    this.db = new DatabaseSync(path)
    this.db.exec('PRAGMA journal_mode = WAL; PRAGMA foreign_keys = ON;')
    this.migrate()
  }

  private migrate(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value_json TEXT NOT NULL, updated_at TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL, status TEXT NOT NULL,
        stage TEXT NOT NULL, progress REAL NOT NULL, completed_items INTEGER NOT NULL,
        total_items INTEGER NOT NULL, config_json TEXT NOT NULL, output_json TEXT,
        error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS model_installations (
        model_id TEXT PRIMARY KEY, local_path TEXT NOT NULL, sha256 TEXT NOT NULL,
        size_bytes INTEGER NOT NULL, imported_at TEXT NOT NULL
      );
      CREATE INDEX IF NOT EXISTS jobs_updated_idx ON jobs(updated_at DESC);
      INSERT OR IGNORE INTO schema_meta(key,value) VALUES('schema_version','2');
      UPDATE schema_meta SET value='2' WHERE key='schema_version';
    `)
  }

  getSettings(): StudioSettings {
    const rows = this.db.prepare('SELECT key, value_json FROM settings').all() as Array<{ key: keyof StudioSettings; value_json: string }>
    const result = { ...defaults }
    for (const row of rows) (result as unknown as Record<string, unknown>)[row.key] = JSON.parse(row.value_json)
    return result
  }

  setSettings(patch: Partial<StudioSettings>): StudioSettings {
    const now = new Date().toISOString()
    const statement = this.db.prepare('INSERT INTO settings(key,value_json,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at')
    this.transaction(() => {
      for (const [key, value] of Object.entries(patch)) statement.run(key, JSON.stringify(value), now)
    })
    return this.getSettings()
  }

  upsertJob(job: JobRecord): void {
    this.db.prepare(`INSERT INTO jobs(id,kind,title,status,stage,progress,completed_items,total_items,config_json,output_json,error,created_at,updated_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
      ON CONFLICT(id) DO UPDATE SET status=excluded.status,stage=excluded.stage,progress=excluded.progress,completed_items=excluded.completed_items,total_items=excluded.total_items,output_json=excluded.output_json,error=excluded.error,updated_at=excluded.updated_at`).run(
      job.id, job.kind, job.title, job.status, job.stage, job.progress, job.completedItems, job.totalItems,
      JSON.stringify(job.config), job.output ? JSON.stringify(job.output) : null, job.error ?? null, job.createdAt, job.updatedAt,
    )
  }

  listJobs(): JobRecord[] {
    const rows = this.db.prepare('SELECT * FROM jobs ORDER BY updated_at DESC LIMIT 500').all() as Array<Record<string, unknown>>
    return rows.map((row) => ({
      id: String(row.id), kind: row.kind as JobRecord['kind'], title: String(row.title), status: row.status as JobRecord['status'], stage: String(row.stage),
      progress: Number(row.progress), completedItems: Number(row.completed_items), totalItems: Number(row.total_items), config: JSON.parse(String(row.config_json)),
      output: row.output_json ? JSON.parse(String(row.output_json)) : undefined, error: row.error ? String(row.error) : undefined,
      createdAt: String(row.created_at), updatedAt: String(row.updated_at),
    }))
  }

  getJob(id: string): JobRecord | undefined { return this.listJobs().find((job) => job.id === id) }

  listModelInstallations(): ModelInstallation[] {
    const rows = this.db.prepare('SELECT model_id, local_path, sha256, size_bytes, imported_at FROM model_installations').all() as Array<Record<string, unknown>>
    return rows.map((row) => ({ modelId: String(row.model_id), localPath: String(row.local_path), sha256: String(row.sha256), sizeBytes: Number(row.size_bytes), importedAt: String(row.imported_at) }))
  }

  getModelInstallation(modelId: string): ModelInstallation | undefined {
    return this.listModelInstallations().find((item) => item.modelId === modelId)
  }

  upsertModelInstallation(item: ModelInstallation): void {
    this.db.prepare(`INSERT INTO model_installations(model_id,local_path,sha256,size_bytes,imported_at) VALUES(?,?,?,?,?)
      ON CONFLICT(model_id) DO UPDATE SET local_path=excluded.local_path,sha256=excluded.sha256,size_bytes=excluded.size_bytes,imported_at=excluded.imported_at`).run(item.modelId, item.localPath, item.sha256, item.sizeBytes, item.importedAt)
  }

  removeModelInstallation(modelId: string): void {
    this.db.prepare('DELETE FROM model_installations WHERE model_id=?').run(modelId)
  }

  private transaction(operation: () => void): void {
    this.db.exec('BEGIN IMMEDIATE')
    try { operation(); this.db.exec('COMMIT') } catch (error) { this.db.exec('ROLLBACK'); throw error }
  }
}
