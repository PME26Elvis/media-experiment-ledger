import { app, dialog, ipcMain, shell } from 'electron'
import { autoUpdater } from 'electron-updater'
import { z } from 'zod'
import { IPC, type CreateJobRequest, type StudioSettings } from '../shared/contracts'
import { StudioDatabase } from './database'
import { engineReady } from './engine'
import { JobManager } from './job-manager'

const pathSchema = z.string().min(1).max(32768)
const createJobSchema = z.object({ kind: z.enum(['scan','atlas','detection','automation','pdf-export','sample-download']), title: z.string().min(1).max(160), config: z.record(z.string(), z.unknown()) })

export function registerIpc(db: StudioDatabase, jobs: JobManager): void {
  ipcMain.handle(IPC.systemInfo, async () => ({ platform: process.platform, arch: process.arch, version: app.getVersion(), appDataPath: app.getPath('userData'), documentsPath: app.getPath('documents'), downloadsPath: app.getPath('downloads'), engineReady: await engineReady() }))
  ipcMain.handle(IPC.chooseDirectory, async (_event, defaultPath?: string) => { const result = await dialog.showOpenDialog({ properties: ['openDirectory','createDirectory'], defaultPath }); return result.canceled ? null : result.filePaths[0] })
  ipcMain.handle(IPC.revealPath, async (_event, rawPath: string) => { const path = pathSchema.parse(rawPath); const error = await shell.openPath(path); return error.length === 0 })
  ipcMain.handle(IPC.settingsGet, () => db.getSettings())
  ipcMain.handle(IPC.settingsSet, (_event, patch: Partial<StudioSettings>) => db.setSettings(patch))
  ipcMain.handle(IPC.jobsList, () => jobs.list())
  ipcMain.handle(IPC.jobsCreate, (_event, request: CreateJobRequest) => jobs.create(createJobSchema.parse(request)))
  ipcMain.handle(IPC.jobsControl, (_event, id: string, action: 'pause'|'resume'|'cancel') => jobs.control(z.string().uuid().parse(id), z.enum(['pause','resume','cancel']).parse(action)))
  ipcMain.handle(IPC.updaterCheck, async () => { try { const result = await autoUpdater.checkForUpdates(); return { status: result?.updateInfo.version === app.getVersion() ? 'current' : 'available', version: result?.updateInfo.version } } catch (error) { return { status: 'error', error: error instanceof Error ? error.message : String(error) } } })
  ipcMain.handle(IPC.updaterInstall, () => { autoUpdater.quitAndInstall(false, true); return true })
}
