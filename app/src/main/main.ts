import {
  app,
  BrowserWindow,
  dialog,
  Menu,
  nativeTheme,
  powerSaveBlocker,
  session,
  Tray,
} from 'electron'
import { existsSync } from 'node:fs'
import { join } from 'node:path'
import { StudioDatabase } from './database'
import { JobManager } from './job-manager'
import { registerIpc } from './ipc'
import { ModelManager } from './model-manager'
import { applyPendingRecovery, createColdStartupBackup, RecoveryManager } from './recovery-manager'
import { ReportManager } from './report-manager'
import { SampleCorpusManager } from './sample-corpus-manager'
import { SecretStore } from './secret-store'
import { UpdateManager } from './update-manager'

let mainWindow: BrowserWindow | null = null
let tray: Tray | null = null
let quitting = false
let database: StudioDatabase | null = null
let jobs: JobManager | null = null
let sleepBlockerId: number | undefined
let sleepMonitor: NodeJS.Timeout | undefined

function rendererPath(): string {
  return join(__dirname, '../../renderer/index.html')
}

function preloadPath(): string {
  return join(__dirname, '../preload/index.js')
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1480,
    height: 940,
    minWidth: 390,
    minHeight: 640,
    show: false,
    backgroundColor: nativeTheme.shouldUseDarkColors ? '#0b1020' : '#f5f7fb',
    webPreferences: {
      preload: preloadPath(),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      spellcheck: true,
    },
  })
  mainWindow.once('ready-to-show', () => mainWindow?.show())
  mainWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (!url.startsWith('file:') && !url.startsWith('http://127.0.0.1:5173')) event.preventDefault()
  })
  if (process.env.VITE_DEV_SERVER_URL) void mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL)
  else void mainWindow.loadFile(rendererPath())

  mainWindow.on('close', event => {
    if (quitting || !database) return
    event.preventDefault()
    const settings = database.getSettings()
    if (settings.closeBehavior === 'tray') {
      mainWindow?.hide()
      return
    }
    if (settings.closeBehavior === 'quit') {
      quitting = true
      app.quit()
      return
    }
    const active = jobs?.activeCount() ?? 0
    void dialog.showMessageBox(mainWindow!, {
      type: active > 0 ? 'warning' : 'question',
      title: 'Close Media Experiment Ledger Studio?',
      message: active > 0
        ? `${active} job(s) are active. Closing the window can keep them running in the system tray.`
        : 'Choose whether to keep the Studio available in the system tray or quit completely.',
      buttons: ['Keep running', 'Quit', 'Cancel'],
      defaultId: 0,
      cancelId: 2,
      noLink: true,
    }).then(result => {
      if (result.response === 0) mainWindow?.hide()
      if (result.response === 1) {
        quitting = true
        app.quit()
      }
    })
  })
}

function createTray(): void {
  const candidates = process.platform === 'win32'
    ? [join(process.resourcesPath, 'icon.ico'), join(__dirname, '../../../resources/icon.ico')]
    : [join(process.resourcesPath, 'icon.png'), join(__dirname, '../../../resources/icon.png')]
  const icon = candidates.find(path => existsSync(path))
  if (!icon) return
  try {
    tray = new Tray(icon)
    tray.setToolTip('Media Experiment Ledger Studio')
    tray.setContextMenu(Menu.buildFromTemplate([
      { label: 'Open Studio', click: () => mainWindow?.show() },
      { label: 'Job Center', click: () => { mainWindow?.show(); void mainWindow?.webContents.executeJavaScript("location.hash='#/jobs'") } },
      { type: 'separator' },
      {
        label: 'Quit',
        click: () => {
          quitting = true
          app.quit()
        },
      },
    ]))
    tray.on('double-click', () => mainWindow?.show())
  } catch {
    tray = null
  }
}

function startSleepMonitor(): void {
  sleepMonitor = setInterval(() => {
    const active = (jobs?.activeCount() ?? 0) > 0
    if (active && sleepBlockerId === undefined) sleepBlockerId = powerSaveBlocker.start('prevent-app-suspension')
    if (!active && sleepBlockerId !== undefined) {
      powerSaveBlocker.stop(sleepBlockerId)
      sleepBlockerId = undefined
    }
  }, 2000)
  sleepMonitor.unref()
}

const hasLock = app.requestSingleInstanceLock()
if (!hasLock) app.quit()
else {
  app.on('second-instance', () => {
    if (!mainWindow) return
    if (mainWindow.isMinimized()) mainWindow.restore()
    mainWindow.show()
    mainWindow.focus()
  })

  app.whenReady().then(async () => {
    session.defaultSession.setPermissionRequestHandler((_webContents, _permission, callback) => callback(false))
    session.defaultSession.setPermissionCheckHandler(() => false)
    const userDataPath = app.getPath('userData')
    applyPendingRecovery(userDataPath)
    createColdStartupBackup(userDataPath, app.getVersion())

    database = new StudioDatabase(join(userDataPath, 'studio.sqlite'))
    const secrets = new SecretStore(userDataPath)
    jobs = new JobManager(database, secrets)
    const interrupted = jobs.recoverInterruptedJobs()
    if (interrupted > 0) database.recordMaintenance('interrupted-jobs-recovered', { count: interrupted })
    const recovery = new RecoveryManager(userDataPath, database, app.getVersion())
    const settings = database.getSettings()
    const updater = new UpdateManager(userDataPath, recovery, jobs, settings.updateChannel ?? 'beta')

    registerIpc(
      database,
      jobs,
      new ModelManager(database, userDataPath),
      secrets,
      new SampleCorpusManager(userDataPath, jobs),
      new ReportManager(userDataPath),
      recovery,
      updater,
    )
    createWindow()
    createTray()
    startSleepMonitor()
    if (settings.checkUpdatesOnLaunch ?? true) void updater.check()
    app.on('activate', () => mainWindow ? mainWindow.show() : createWindow())
  })
}

app.on('before-quit', () => {
  quitting = true
  jobs?.recoverInterruptedJobs()
  database?.checkpoint()
})

app.on('will-quit', () => {
  if (sleepMonitor) clearInterval(sleepMonitor)
  if (sleepBlockerId !== undefined) powerSaveBlocker.stop(sleepBlockerId)
  database?.close()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin' && !tray) app.quit()
})
