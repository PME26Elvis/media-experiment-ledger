import { randomUUID } from 'node:crypto'
import { existsSync, mkdirSync, readFileSync, readdirSync, renameSync, rmSync, writeFileSync } from 'node:fs'
import { basename, dirname, join, resolve, sep } from 'node:path'
import { z } from 'zod'
import type { AppliedReportTemplate, CustomReportTemplateSummary, ReportTemplateDefinition } from '../shared/template-contracts'

const color = z.string().regex(/^#[0-9a-f]{6}$/iu)
const definitionSchema = z.object({
  schemaVersion: z.literal(1),
  name: z.string().min(1).max(120),
  description: z.string().max(1000),
  page: z.object({
    widthInches: z.number().min(4).max(30),
    heightInches: z.number().min(4).max(30),
  }),
  marginInches: z.number().min(0.1).max(2.5),
  colors: z.object({
    background: color,
    surface: color,
    text: color,
    muted: color,
    primary: color,
    accent: color,
  }),
  fontFamily: z.string().min(1).max(200).regex(/^[A-Za-z0-9 ,.'"-]+$/u),
})
const customSchema = z.object({
  id: z.string().regex(/^custom-[0-9a-f-]{36}$/u),
  definition: definitionSchema,
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
})
const appliedSchema = z.object({
  documentId: z.string().uuid(),
  customTemplateId: z.string().regex(/^custom-[0-9a-f-]{36}$/u),
  definition: definitionSchema,
  appliedAt: z.string().datetime(),
})

function atomicJson(path: string, value: unknown): void {
  mkdirSync(dirname(path), { recursive: true })
  const temporary = `${path}.${randomUUID()}.tmp`
  writeFileSync(temporary, JSON.stringify(value, null, 2), 'utf8')
  renameSync(temporary, path)
}

function safeId(id: string): string {
  if (!/^custom-[0-9a-f-]{36}$/u.test(id)) throw new Error('Invalid custom template ID.')
  return id
}

export class TemplateManager {
  private readonly templatesRoot: string
  private readonly snapshotsRoot: string
  private readonly documentsRoot: string

  constructor(userDataPath: string) {
    this.templatesRoot = join(userDataPath, 'reports', 'templates')
    this.snapshotsRoot = join(userDataPath, 'reports', 'template-snapshots')
    this.documentsRoot = join(userDataPath, 'reports', 'documents')
    mkdirSync(this.templatesRoot, { recursive: true })
    mkdirSync(this.snapshotsRoot, { recursive: true })
  }

  list(): CustomReportTemplateSummary[] {
    return readdirSync(this.templatesRoot)
      .filter(name => name.endsWith('.json'))
      .flatMap(name => {
        try {
          return [customSchema.parse(JSON.parse(readFileSync(join(this.templatesRoot, name), 'utf8'))) as CustomReportTemplateSummary]
        } catch {
          return []
        }
      })
      .sort((a, b) => a.definition.name.localeCompare(b.definition.name))
  }

  import(path: string): CustomReportTemplateSummary {
    const definition = definitionSchema.parse(JSON.parse(readFileSync(resolve(path), 'utf8'))) as ReportTemplateDefinition
    const now = new Date().toISOString()
    const record: CustomReportTemplateSummary = {
      id: `custom-${randomUUID()}`,
      definition,
      createdAt: now,
      updatedAt: now,
    }
    atomicJson(this.path(record.id), record)
    return record
  }

  export(id: string, outputDirectory: string): string {
    const record = this.get(id)
    const root = resolve(outputDirectory)
    mkdirSync(root, { recursive: true })
    const name = record.definition.name.replace(/[^A-Za-z0-9\u4e00-\u9fff._-]+/gu, '-').replace(/^-+|-+$/gu, '') || 'report-template'
    const path = join(root, `${name}.mel-report-template.json`)
    atomicJson(path, record.definition)
    return path
  }

  remove(id: string): boolean {
    const path = this.path(id)
    if (!existsSync(path)) return false
    rmSync(path, { force: true })
    return true
  }

  apply(documentId: string, templateId: string): AppliedReportTemplate {
    if (!/^[0-9a-f-]{36}$/iu.test(documentId)) throw new Error('Invalid report document ID.')
    if (!existsSync(join(this.documentsRoot, `${documentId}.json`))) throw new Error('Report document does not exist.')
    const record = this.get(templateId)
    const applied: AppliedReportTemplate = {
      documentId,
      customTemplateId: record.id,
      definition: structuredClone(record.definition),
      appliedAt: new Date().toISOString(),
    }
    atomicJson(this.snapshotPath(documentId), applied)
    return applied
  }

  applied(documentId: string): AppliedReportTemplate | null {
    const path = this.snapshotPath(documentId)
    if (!existsSync(path)) return null
    return appliedSchema.parse(JSON.parse(readFileSync(path, 'utf8'))) as AppliedReportTemplate
  }

  templateForDocument(documentId: string): ReportTemplateDefinition | undefined {
    return this.applied(documentId)?.definition
  }

  private get(id: string): CustomReportTemplateSummary {
    return customSchema.parse(JSON.parse(readFileSync(this.path(id), 'utf8'))) as CustomReportTemplateSummary
  }

  private path(id: string): string {
    return join(this.templatesRoot, `${safeId(id)}.json`)
  }

  private snapshotPath(documentId: string): string {
    const root = resolve(this.snapshotsRoot)
    const path = resolve(this.snapshotsRoot, `${documentId}.json`)
    if (!path.startsWith(`${root}${sep}`)) throw new Error('Template snapshot path escapes its managed root.')
    return path
  }
}
