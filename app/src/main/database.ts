import Database from 'better-sqlite3'
import { mkdirSync } from 'node:fs'
import { dirname } from 'node:path'
import type { JobRecord, StudioSettings } from '../shared/contracts'

const defaults: StudioSettings = {
  locale: 'zh-TW', appearance: 'system', imageInputPath: '', videoInputPath: '', atlasOutputPath: '', detectionOutputPath: '', generatedOutputPath: '', closeBehavior: 'ask', reducedMotion: false,
}

export class StudioDatabase {
  private readonly db: Database.Database

  constructor(path: string) {
    mkdirSync(dirname(path), { recursive: true })
    this.db = new Database(path)
    this.db.pragma('journal_mode = WAL')
    this.db.pragma('foreign_keys = ON')
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
      CREATE INDEX IF NOT EXISTS jobs_updated_idx ON jobs(updated_at DESC);
    `)
    this.db.prepare(`INSERT INTO schema_meta(key,value) VALUES('schema_version','1') ON CONFLICT(key) DO NOTHING`).run()
  }

  getSettings(): StudioSettings {
    const rows = this.db.prepare('SELECT key, value_json FROM settings').all() as Array<{ key: keyof StudioSettings; value_json: string }>
    const result = { ...defaults }
    for (const row of rows) (result as unknown as Record<string, unknown>)[row.key] = JSON.parse(row.value_json)
    return result
  }

  setSettings(patch: Partial<StudioSettings>): StudioSettings {
    const now = new Date().toISOString()
    const statement = this.db.prepare(`INSERT INTO settings(key,value_json,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at`)
    const transaction = this.db.transaction(() => {
      for (const [key, value] of Object.entries(patch)) statement.run(key, JSON.stringify(value), now)
    })
    transaction()
    return this.getSettings()
  }

  upsertJob(job: JobRecord): void {
    this.db.prepare(`INSERT INTO jobs(id,kind,title,status,stage,progress,completed_items,total_items,config_json,output_json,error,created_at,updated_at)
      VALUES(@id,@kind,@title,@status,@stage,@progress,@completedItems,@totalItems,@configJson,@outputJson,@error,@createdAt,@updatedAt)
      ON CONFLICT(id) DO UPDATE SET status=@status,stage=@stage,progress=@progress,completed_items=@completedItems,total_items=@totalItems,output_json=@outputJson,error=@error,updated_at=@updatedAt`).run({
      ...job, configJson: JSON.stringify(job.config), outputJson: job.output ? JSON.stringify(job.output) : null, error: job.error ?? null,
    })
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
}
