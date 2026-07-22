import { mkdirSync } from 'node:fs'
import { dirname } from 'node:path'
import { DatabaseSync } from 'node:sqlite'
import type { JobRecord, StudioSettings } from '../shared/contracts'

const CURRENT_SCHEMA_VERSION = 4

const defaults: StudioSettings = {
  locale: 'zh-TW',
  appearance: 'system',
  imageInputPath: '',
  videoInputPath: '',
  atlasOutputPath: '',
  detectionOutputPath: '',
  generatedOutputPath: '',
  closeBehavior: 'ask',
  reducedMotion: false,
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
    this.db.exec('PRAGMA journal_mode = WAL; PRAGMA foreign_keys = ON; PRAGMA busy_timeout = 5000;')
    this.migrate()
  }

  private migrate(): void {
    this.transaction(() => {
      this.db.exec(`
        CREATE TABLE IF NOT EXISTS schema_meta (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS migration_history (
          version INTEGER PRIMARY KEY,
          applied_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (
          key TEXT PRIMARY KEY,
          value_json TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS jobs (
          id TEXT PRIMARY KEY,
          kind TEXT NOT NULL,
          title TEXT NOT NULL,
          status TEXT NOT NULL,
          stage TEXT NOT NULL,
          progress REAL NOT NULL,
          completed_items INTEGER NOT NULL,
          total_items INTEGER NOT NULL,
          config_json TEXT NOT NULL,
          output_json TEXT,
          error TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS model_installations (
          model_id TEXT PRIMARY KEY,
          local_path TEXT NOT NULL,
          sha256 TEXT NOT NULL,
          size_bytes INTEGER NOT NULL,
          imported_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS app_runs (
          id TEXT PRIMARY KEY,
          version TEXT NOT NULL,
          platform TEXT NOT NULL,
          architecture TEXT NOT NULL,
          started_at TEXT NOT NULL,
          ended_at TEXT,
          clean_exit INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS maintenance_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          kind TEXT NOT NULL,
          detail_json TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS jobs_updated_idx ON jobs(updated_at DESC);
        CREATE INDEX IF NOT EXISTS maintenance_created_idx ON maintenance_events(created_at DESC);
      `)
      const now = new Date().toISOString()
      const history = this.db.prepare('INSERT OR IGNORE INTO migration_history(version,applied_at) VALUES(?,?)')
      for (let version = 1; version <= CURRENT_SCHEMA_VERSION; version += 1) history.run(version, now)
      this.db.prepare(`INSERT INTO schema_meta(key,value) VALUES('schema_version',?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value`).run(String(CURRENT_SCHEMA_VERSION))
    })
  }

  schemaVersion(): number {
    const row = this.db.prepare("SELECT value FROM schema_meta WHERE key='schema_version'").get() as { value?: string } | undefined
    return Number(row?.value ?? 0)
  }

  checkpoint(): void {
    this.db.exec('PRAGMA wal_checkpoint(TRUNCATE);')
  }

  integrityCheck(): { ok: boolean; messages: string[]; schemaVersion: number } {
    const rows = this.db.prepare('PRAGMA integrity_check').all() as Array<{ integrity_check?: string }>
    const messages = rows.map(row => String(row.integrity_check ?? 'unknown'))
    return {
      ok: messages.length === 1 && messages[0] === 'ok',
      messages,
      schemaVersion: this.schemaVersion(),
    }
  }

  recordMaintenance(kind: string, detail: unknown): void {
    this.db.prepare('INSERT INTO maintenance_events(kind,detail_json,created_at) VALUES(?,?,?)')
      .run(kind.slice(0, 100), JSON.stringify(detail), new Date().toISOString())
  }

  getSettings(): StudioSettings {
    const rows = this.db.prepare('SELECT key, value_json FROM settings').all() as Array<{
      key: keyof StudioSettings
      value_json: string
    }>
    const result = { ...defaults }
    for (const row of rows) {
      try {
        ;(result as unknown as Record<string, unknown>)[row.key] = JSON.parse(row.value_json)
      } catch {
        this.recordMaintenance('invalid-setting-json', { key: row.key })
      }
    }
    return result
  }

  setSettings(patch: Partial<StudioSettings>): StudioSettings {
    const now = new Date().toISOString()
    const statement = this.db.prepare(`INSERT INTO settings(key,value_json,updated_at) VALUES(?,?,?)
      ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at`)
    this.transaction(() => {
      for (const [key, value] of Object.entries(patch)) statement.run(key, JSON.stringify(value), now)
    })
    return this.getSettings()
  }

  upsertJob(job: JobRecord): void {
    this.db.prepare(`INSERT INTO jobs(
        id,kind,title,status,stage,progress,completed_items,total_items,
        config_json,output_json,error,created_at,updated_at
      ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
      ON CONFLICT(id) DO UPDATE SET
        status=excluded.status,
        stage=excluded.stage,
        progress=excluded.progress,
        completed_items=excluded.completed_items,
        total_items=excluded.total_items,
        output_json=excluded.output_json,
        error=excluded.error,
        updated_at=excluded.updated_at`).run(
      job.id,
      job.kind,
      job.title,
      job.status,
      job.stage,
      job.progress,
      job.completedItems,
      job.totalItems,
      JSON.stringify(job.config),
      job.output ? JSON.stringify(job.output) : null,
      job.error ?? null,
      job.createdAt,
      job.updatedAt,
    )
  }

  listJobs(): JobRecord[] {
    const rows = this.db.prepare('SELECT * FROM jobs ORDER BY updated_at DESC LIMIT 500').all() as Array<Record<string, unknown>>
    return rows.map(row => ({
      id: String(row.id),
      kind: row.kind as JobRecord['kind'],
      title: String(row.title),
      status: row.status as JobRecord['status'],
      stage: String(row.stage),
      progress: Number(row.progress),
      completedItems: Number(row.completed_items),
      totalItems: Number(row.total_items),
      config: JSON.parse(String(row.config_json)),
      output: row.output_json ? JSON.parse(String(row.output_json)) : undefined,
      error: row.error ? String(row.error) : undefined,
      createdAt: String(row.created_at),
      updatedAt: String(row.updated_at),
    }))
  }

  getJob(id: string): JobRecord | undefined {
    const row = this.db.prepare('SELECT * FROM jobs WHERE id=?').get(id) as Record<string, unknown> | undefined
    if (!row) return undefined
    return {
      id: String(row.id),
      kind: row.kind as JobRecord['kind'],
      title: String(row.title),
      status: row.status as JobRecord['status'],
      stage: String(row.stage),
      progress: Number(row.progress),
      completedItems: Number(row.completed_items),
      totalItems: Number(row.total_items),
      config: JSON.parse(String(row.config_json)),
      output: row.output_json ? JSON.parse(String(row.output_json)) : undefined,
      error: row.error ? String(row.error) : undefined,
      createdAt: String(row.created_at),
      updatedAt: String(row.updated_at),
    }
  }

  listModelInstallations(): ModelInstallation[] {
    const rows = this.db.prepare('SELECT model_id, local_path, sha256, size_bytes, imported_at FROM model_installations').all() as Array<Record<string, unknown>>
    return rows.map(row => ({
      modelId: String(row.model_id),
      localPath: String(row.local_path),
      sha256: String(row.sha256),
      sizeBytes: Number(row.size_bytes),
      importedAt: String(row.imported_at),
    }))
  }

  getModelInstallation(modelId: string): ModelInstallation | undefined {
    return this.listModelInstallations().find(item => item.modelId === modelId)
  }

  upsertModelInstallation(item: ModelInstallation): void {
    this.db.prepare(`INSERT INTO model_installations(model_id,local_path,sha256,size_bytes,imported_at) VALUES(?,?,?,?,?)
      ON CONFLICT(model_id) DO UPDATE SET
        local_path=excluded.local_path,
        sha256=excluded.sha256,
        size_bytes=excluded.size_bytes,
        imported_at=excluded.imported_at`).run(
      item.modelId,
      item.localPath,
      item.sha256,
      item.sizeBytes,
      item.importedAt,
    )
  }

  removeModelInstallation(modelId: string): void {
    this.db.prepare('DELETE FROM model_installations WHERE model_id=?').run(modelId)
  }

  close(): void {
    this.checkpoint()
    this.db.close()
  }

  private transaction(operation: () => void): void {
    this.db.exec('BEGIN IMMEDIATE')
    try {
      operation()
      this.db.exec('COMMIT')
    } catch (error) {
      this.db.exec('ROLLBACK')
      throw error
    }
  }
}
