import { BrowserWindow } from 'electron'
import { createHash, randomUUID } from 'node:crypto'
import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  renameSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import { basename, dirname, join, resolve, sep } from 'node:path'
import { z } from 'zod'
import type {
  ReportBlock,
  ReportDocument,
  ReportExportResult,
  ReportRevisionSummary,
  ReportSummary,
} from '../shared/contracts'
import { reportTemplate } from '../shared/report-templates'
import { renderReportHtml } from './report-renderer'
import type { TemplateManager } from './template-manager'

const templateIds = [
  'research-light',
  'editorial-dark',
  'gallery-minimal',
  'technical-audit',
  'executive-review',
  'traditional-chinese-academic',
  'presentation-16-9',
] as const

const styleSchema = z.object({
  fontFamily: z.enum(['sans', 'serif', 'mono']),
  fontSize: z.number().min(8).max(96),
  fontWeight: z.union([
    z.literal(400),
    z.literal(500),
    z.literal(600),
    z.literal(700),
    z.literal(800),
  ]),
  italic: z.boolean(),
  underline: z.boolean(),
  alignment: z.enum(['left', 'center', 'right', 'justify']),
  color: z.string().regex(/^#[0-9a-f]{6}$/iu),
  lineHeight: z.number().min(1).max(2.5),
})

const layoutSchema = z.object({
  mode: z.enum(['structured', 'freeform']),
  span: z.union([z.literal(1), z.literal(2)]),
  page: z.number().int().positive(),
  x: z.number().min(0).max(100),
  y: z.number().min(0).max(100),
  width: z.number().min(5).max(100),
  height: z.number().min(2).max(100),
})

const blockSchema = z.object({
  id: z.string().uuid(),
  type: z.enum([
    'heading',
    'rich-text',
    'image',
    'atlas-page',
    'callout',
    'statistics',
    'page-break',
  ]),
  layout: layoutSchema,
  style: styleSchema,
  text: z.string().max(200_000).optional(),
  imagePath: z.string().max(32_768).optional(),
  caption: z.string().max(10_000).optional(),
  imageFit: z.enum(['contain', 'cover']).optional(),
  tone: z.enum(['info', 'success', 'warning', 'error']).optional(),
  statistics: z.array(
    z.object({
      label: z.string().max(1_000),
      value: z.string().max(1_000),
    }),
  ).optional(),
})

const documentSchema = z.object({
  schemaVersion: z.literal(1),
  id: z.string().uuid(),
  title: z.string().min(1).max(300),
  subtitle: z.string().max(2_000),
  template: z.enum(templateIds),
  blocks: z.array(blockSchema).max(5_000),
  sourceAtlasManifest: z.string().max(32_768).optional(),
  revision: z.number().int().positive(),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
})

const defaultStyle = {
  fontFamily: 'sans' as const,
  fontSize: 18,
  fontWeight: 400 as const,
  italic: false,
  underline: false,
  alignment: 'left' as const,
  color: '#172033',
  lineHeight: 1.5,
}

const defaultLayout = {
  mode: 'structured' as const,
  span: 2 as const,
  page: 1,
  x: 5,
  y: 5,
  width: 90,
  height: 10,
}

function atomicJson(path: string, value: unknown): void {
  mkdirSync(dirname(path), { recursive: true })
  const temporary = `${path}.tmp`
  writeFileSync(temporary, JSON.stringify(value, null, 2), 'utf8')
  renameSync(temporary, path)
}

function sha256(data: Buffer | string): string {
  return createHash('sha256').update(data).digest('hex')
}

function slug(value: string): string {
  return value
    .normalize('NFKD')
    .replace(/[^a-zA-Z0-9\u4e00-\u9fff]+/gu, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80) || 'report'
}

export class ReportManager {
  private readonly documentsRoot: string
  private readonly revisionsRoot: string
  private readonly tempRoot: string

  constructor(
    userDataPath: string,
    private readonly templates?: Pick<TemplateManager, 'templateForDocument'>,
  ) {
    this.documentsRoot = join(userDataPath, 'reports', 'documents')
    this.revisionsRoot = join(userDataPath, 'reports', 'revisions')
    this.tempRoot = join(userDataPath, 'reports', 'temp')
    mkdirSync(this.documentsRoot, { recursive: true })
    mkdirSync(this.revisionsRoot, { recursive: true })
    mkdirSync(this.tempRoot, { recursive: true })
  }

  list(): ReportSummary[] {
    return readdirSync(this.documentsRoot, { withFileTypes: true })
      .filter((entry) => entry.isFile() && entry.name.endsWith('.json'))
      .map((entry) => this.read(join(this.documentsRoot, entry.name)))
      .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
      .map((document) => ({
        id: document.id,
        title: document.title,
        subtitle: document.subtitle,
        template: document.template,
        revision: document.revision,
        blockCount: document.blocks.length,
        updatedAt: document.updatedAt,
        sourceAtlasManifest: document.sourceAtlasManifest,
      }))
  }

  create(title = 'Untitled Atlas Report'): ReportDocument {
    const now = new Date().toISOString()
    const document: ReportDocument = {
      schemaVersion: 1,
      id: randomUUID(),
      title,
      subtitle: 'Evidence report created with Media Experiment Ledger Studio',
      template: 'research-light',
      revision: 1,
      createdAt: now,
      updatedAt: now,
      blocks: [
        {
          id: randomUUID(),
          type: 'heading',
          layout: { ...defaultLayout },
          style: { ...defaultStyle, fontSize: 42, fontWeight: 800 },
          text: title,
        },
        {
          id: randomUUID(),
          type: 'rich-text',
          layout: { ...defaultLayout },
          style: { ...defaultStyle },
          text: 'Write the report introduction here.',
        },
      ],
    }
    atomicJson(this.path(document.id), document)
    return document
  }

  get(id: string): ReportDocument {
    return this.read(this.path(id))
  }

  save(input: ReportDocument, checkpoint = false): ReportDocument {
    const parsed = documentSchema.parse(input) as ReportDocument
    const path = this.path(parsed.id)
    const existing = existsSync(path) ? this.read(path) : undefined

    if (checkpoint && existing) {
      const revisionRoot = join(this.revisionsRoot, parsed.id)
      mkdirSync(revisionRoot, { recursive: true })
      atomicJson(
        join(revisionRoot, `r${existing.revision}-${Date.now()}.json`),
        existing,
      )
    }

    const saved: ReportDocument = {
      ...parsed,
      revision: checkpoint
        ? (existing?.revision ?? parsed.revision) + 1
        : parsed.revision,
      updatedAt: new Date().toISOString(),
    }
    atomicJson(path, saved)
    return saved
  }

  delete(id: string): boolean {
    const path = this.path(id)
    if (!existsSync(path)) return false
    rmSync(path, { force: true })
    return true
  }

  importAtlas(manifestPath: string): ReportDocument {
    const resolved = resolve(manifestPath)
    const manifest = JSON.parse(readFileSync(resolved, 'utf8')) as {
      pages?: Array<{ path?: string }>
    }
    const document = this.create(`Atlas Report · ${basename(dirname(resolved))}`)
    document.sourceAtlasManifest = resolved
    document.template = 'technical-audit'

    const importedPages: ReportBlock[] = (manifest.pages ?? [])
      .filter((page) => Boolean(page.path))
      .map((page, index) => ({
        id: randomUUID(),
        type: 'atlas-page',
        layout: { ...defaultLayout, page: index + 2 },
        style: { ...defaultStyle },
        imagePath: resolve(String(page.path)),
        caption: `Atlas evidence page ${index + 1}`,
        imageFit: 'contain',
      }))

    document.blocks = [
      {
        id: randomUUID(),
        type: 'heading',
        layout: { ...defaultLayout },
        style: { ...defaultStyle, fontSize: 38, fontWeight: 800 },
        text: document.title,
      },
      {
        id: randomUUID(),
        type: 'rich-text',
        layout: { ...defaultLayout },
        style: { ...defaultStyle },
        text: 'Imported from an immutable Atlas analysis manifest.',
      },
      ...importedPages,
    ]
    return this.save(document, true)
  }

  revisions(id: string): ReportRevisionSummary[] {
    const root = join(this.revisionsRoot, id)
    if (!existsSync(root)) return []
    return readdirSync(root)
      .filter((name) => name.endsWith('.json'))
      .map((name) => {
        const path = join(root, name)
        const document = this.read(path)
        return {
          id: document.id,
          revision: document.revision,
          createdAt: document.updatedAt,
          path,
        }
      })
      .sort((a, b) => b.revision - a.revision)
  }

  restore(id: string, revisionPath: string): ReportDocument {
    const root = resolve(join(this.revisionsRoot, id))
    const requested = resolve(revisionPath)
    if (!requested.startsWith(`${root}${sep}`)) {
      throw new Error('Revision path is outside the report revision store.')
    }
    const snapshot = this.read(requested)
    const current = this.get(id)
    return this.save(
      {
        ...snapshot,
        id: current.id,
        createdAt: current.createdAt,
        revision: current.revision,
      },
      true,
    )
  }

  async exportPdf(
    id: string,
    outputDirectory: string,
  ): Promise<ReportExportResult> {
    const document = this.get(id)
    const customTemplate = this.templates?.templateForDocument(document.id)
    const builtInTemplate = reportTemplate(document.template)
    const rendered = renderReportHtml(document, customTemplate)
    const page = customTemplate?.page ?? builtInTemplate.page
    const outputRoot = resolve(outputDirectory)
    mkdirSync(outputRoot, { recursive: true })
    const htmlPath = join(this.tempRoot, `${document.id}-${Date.now()}.html`)
    writeFileSync(htmlPath, rendered.html, 'utf8')

    const reportWindow = new BrowserWindow({
      show: false,
      webPreferences: {
        sandbox: true,
        contextIsolation: true,
        nodeIntegration: false,
        webSecurity: true,
      },
    })

    try {
      await reportWindow.loadFile(htmlPath)
      const pdf = await reportWindow.webContents.printToPDF({
        printBackground: true,
        preferCSSPageSize: true,
        generateTaggedPDF: true,
        generateDocumentOutline: true,
        pageSize: {
          width: page.widthInches,
          height: page.heightInches,
        },
        margins: { top: 0, bottom: 0, left: 0, right: 0 },
      })
      const pdfPath = join(
        outputRoot,
        `${slug(document.title)}-r${document.revision}.pdf`,
      )
      const temporary = `${pdfPath}.tmp`
      writeFileSync(temporary, pdf)
      renameSync(temporary, pdfPath)
      const digest = sha256(pdf)
      const manifestPath = `${pdfPath}.manifest.json`
      atomicJson(manifestPath, {
        schema_version: 1,
        document_id: document.id,
        document_revision: document.revision,
        document_sha256: sha256(JSON.stringify(document)),
        template: customTemplate
          ? { kind: 'custom-snapshot', definition: customTemplate }
          : { kind: 'built-in', id: document.template },
        pdf_path: pdfPath,
        pdf_sha256: digest,
        pdf_size_bytes: pdf.length,
        warnings: rendered.warnings,
        exported_at: new Date().toISOString(),
      })
      return {
        pdfPath,
        manifestPath,
        sha256: digest,
        sizeBytes: pdf.length,
        warnings: rendered.warnings,
      }
    } finally {
      reportWindow.destroy()
      rmSync(htmlPath, { force: true })
    }
  }

  private path(id: string): string {
    return join(this.documentsRoot, `${id}.json`)
  }

  private read(path: string): ReportDocument {
    return documentSchema.parse(
      JSON.parse(readFileSync(path, 'utf8')),
    ) as ReportDocument
  }
}
