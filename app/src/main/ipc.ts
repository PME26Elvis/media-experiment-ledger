import { app, dialog, ipcMain, shell } from 'electron'
import { z } from 'zod'
import { IPC, type CreateJobRequest, type ReportDocument, type StudioSettings } from '../shared/contracts'
import { StudioDatabase } from './database'
import { engineReady } from './engine'
import { JobManager } from './job-manager'
import { ModelManager } from './model-manager'
import { RecoveryManager } from './recovery-manager'
import { ReportManager } from './report-manager'
import { SampleCorpusManager } from './sample-corpus-manager'
import { SecretStore } from './secret-store'
import { UpdateManager } from './update-manager'

const pathSchema = z.string().min(1).max(32768)
const uuidSchema = z.string().uuid()
const createJobSchema = z.object({
  kind: z.enum(['scan', 'atlas', 'detection', 'automation', 'pdf-export', 'sample-download']),
  title: z.string().min(1).max(160),
  config: z.record(z.string(), z.unknown()),
})
const secretSchema = z.object({
  id: z.string().uuid().optional(),
  name: z.string().min(1).max(120),
  provider: z.string().min(1).max(80),
  environmentVariable: z.string().regex(/^[A-Z_][A-Z0-9_]*$/u),
  backend: z.enum(['os', 'session', 'env', 'portable-vault']),
  secret: z.string().max(65536).optional(),
  password: z.string().max(4096).optional(),
  envFilePath: z.string().max(32768).optional(),
})
const settingsPatchSchema = z.object({
  locale: z.enum(['zh-TW', 'en', 'zh-CN', 'ja', 'ko']).optional(),
  appearance: z.enum(['system', 'light', 'dark']).optional(),
  imageInputPath: z.string().max(32768).optional(),
  videoInputPath: z.string().max(32768).optional(),
  atlasOutputPath: z.string().max(32768).optional(),
  detectionOutputPath: z.string().max(32768).optional(),
  generatedOutputPath: z.string().max(32768).optional(),
  closeBehavior: z.enum(['ask', 'tray', 'quit']).optional(),
  reducedMotion: z.boolean().optional(),
  updateChannel: z.enum(['alpha', 'beta', 'stable']).optional(),
  checkUpdatesOnLaunch: z.boolean().optional(),
})

export function registerIpc(
  db: StudioDatabase,
  jobs: JobManager,
  models: ModelManager,
  secrets: SecretStore,
  corpora: SampleCorpusManager,
  reports: ReportManager,
  recovery: RecoveryManager,
  updater: UpdateManager,
): void {
  ipcMain.handle(IPC.systemInfo, async () => ({
    platform: process.platform,
    arch: process.arch,
    version: app.getVersion(),
    appDataPath: app.getPath('userData'),
    documentsPath: app.getPath('documents'),
    downloadsPath: app.getPath('downloads'),
    engineReady: await engineReady(),
    schemaVersion: db.schemaVersion(),
    updateMode: process.platform === 'linux' ? 'manual' : 'automatic',
  }))
  ipcMain.handle(IPC.chooseDirectory, async (_event, defaultPath?: string) => {
    const result = await dialog.showOpenDialog({ properties: ['openDirectory', 'createDirectory'], defaultPath })
    return result.canceled ? null : result.filePaths[0]
  })
  ipcMain.handle(IPC.chooseFile, async (_event, options?: { title?: string; extensions?: string[] }) => {
    const result = await dialog.showOpenDialog({
      title: options?.title,
      properties: ['openFile'],
      filters: options?.extensions?.length ? [{ name: 'Supported files', extensions: options.extensions }] : undefined,
    })
    return result.canceled ? null : result.filePaths[0]
  })
  ipcMain.handle(IPC.revealPath, async (_event, rawPath: string) => {
    const path = pathSchema.parse(rawPath)
    const error = await shell.openPath(path)
    return error.length === 0
  })

  ipcMain.handle(IPC.settingsGet, () => db.getSettings())
  ipcMain.handle(IPC.settingsSet, (_event, patch: Partial<StudioSettings>) => {
    const parsed = settingsPatchSchema.parse(patch)
    if (parsed.updateChannel) updater.setChannel(parsed.updateChannel)
    return db.setSettings(parsed)
  })

  ipcMain.handle(IPC.jobsList, () => jobs.list())
  ipcMain.handle(IPC.jobsCreate, (_event, request: CreateJobRequest) => jobs.create(createJobSchema.parse(request)))
  ipcMain.handle(IPC.jobsControl, (_event, id: string, action: 'pause' | 'resume' | 'cancel') =>
    jobs.control(uuidSchema.parse(id), z.enum(['pause', 'resume', 'cancel']).parse(action)))

  ipcMain.handle(IPC.modelsList, () => models.list())
  ipcMain.handle(IPC.modelsImport, (_event, modelId: string, sourcePath: string) =>
    models.import(z.string().min(1).parse(modelId), pathSchema.parse(sourcePath)))
  ipcMain.handle(IPC.modelsRemove, (_event, modelId: string) => models.remove(z.string().min(1).parse(modelId)))

  ipcMain.handle(IPC.secretsList, () => secrets.list())
  ipcMain.handle(IPC.secretsSave, (_event, request: unknown) => secrets.save(secretSchema.parse(request)))
  ipcMain.handle(IPC.secretsRemove, (_event, id: string) => secrets.remove(uuidSchema.parse(id)))
  ipcMain.handle(IPC.secretsUnlock, (_event, id: string, password: string) =>
    secrets.unlock(uuidSchema.parse(id), z.string().min(1).max(4096).parse(password)))
  ipcMain.handle(IPC.secretsLock, (_event, id: string) => secrets.lock(uuidSchema.parse(id)))

  ipcMain.handle(IPC.corporaList, () => corpora.list())
  ipcMain.handle(IPC.corporaRefresh, () => corpora.refreshRemote())
  ipcMain.handle(IPC.corporaImport, (_event, path: string) => corpora.importManifest(pathSchema.parse(path)))
  ipcMain.handle(IPC.corporaInstall, (_event, id: string) => corpora.install(z.string().min(1).parse(id)))
  ipcMain.handle(IPC.corporaRemove, (_event, id: string) => corpora.remove(z.string().min(1).parse(id)))

  ipcMain.handle(IPC.reportsList, () => reports.list())
  ipcMain.handle(IPC.reportsCreate, (_event, title?: string) => reports.create(title))
  ipcMain.handle(IPC.reportsGet, (_event, id: string) => reports.get(uuidSchema.parse(id)))
  ipcMain.handle(IPC.reportsSave, (_event, document: ReportDocument, checkpoint?: boolean) =>
    reports.save(document, Boolean(checkpoint)))
  ipcMain.handle(IPC.reportsDelete, (_event, id: string) => reports.delete(uuidSchema.parse(id)))
  ipcMain.handle(IPC.reportsImportAtlas, (_event, path: string) => reports.importAtlas(pathSchema.parse(path)))
  ipcMain.handle(IPC.reportsExportPdf, (_event, id: string, outputDirectory: string) =>
    reports.exportPdf(uuidSchema.parse(id), pathSchema.parse(outputDirectory)))
  ipcMain.handle(IPC.reportsRevisions, (_event, id: string) => reports.revisions(uuidSchema.parse(id)))
  ipcMain.handle(IPC.reportsRestore, (_event, id: string, revisionPath: string) =>
    reports.restore(uuidSchema.parse(id), pathSchema.parse(revisionPath)))

  ipcMain.handle(IPC.recoveryList, () => recovery.list())
  ipcMain.handle(IPC.recoveryCreate, (_event, reason: string) =>
    recovery.create(z.string().min(1).max(300).parse(reason)))
  ipcMain.handle(IPC.recoveryIntegrity, () => db.integrityCheck())
  ipcMain.handle(IPC.recoveryRemove, (_event, id: string) => recovery.remove(z.string().min(1).max(160).parse(id)))
  ipcMain.handle(IPC.recoveryRestore, async (_event, id: string) => {
    await jobs.pauseAll()
    const result = recovery.scheduleRestore(z.string().min(1).max(160).parse(id))
    setImmediate(() => {
      app.relaunch()
      app.exit(0)
    })
    return result
  })

  ipcMain.handle(IPC.updaterStatus, () => updater.status())
  ipcMain.handle(IPC.updaterCheck, () => updater.check())
  ipcMain.handle(IPC.updaterDownload, () => updater.download())
  ipcMain.handle(IPC.updaterInstall, () => updater.install())
  ipcMain.handle(IPC.updaterImportOffline, (_event, manifestPath: string, packagePath: string) =>
    updater.importOffline(pathSchema.parse(manifestPath), pathSchema.parse(packagePath)))
  ipcMain.handle(IPC.updaterOpenOffline, () => updater.openOffline())
}
