import { app, BrowserWindow, nativeTheme, session, Tray, Menu } from 'electron'
import { join } from 'node:path'
import { StudioDatabase } from './database'
import { JobManager } from './job-manager'
import { registerIpc } from './ipc'

let mainWindow: BrowserWindow | null = null
let tray: Tray | null = null
let quitting = false

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1480, height: 940, minWidth: 390, minHeight: 640, show: false,
    backgroundColor: nativeTheme.shouldUseDarkColors ? '#0b1020' : '#f5f7fb',
    webPreferences: { preload: join(__dirname, '../preload/index.js'), contextIsolation: true, nodeIntegration: false, sandbox: true, webSecurity: true },
  })
  mainWindow.once('ready-to-show', () => mainWindow?.show())
  mainWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
  mainWindow.webContents.on('will-navigate', (event, url) => { if (!url.startsWith('file:') && !url.startsWith('http://127.0.0.1:5173')) event.preventDefault() })
  if (process.env.VITE_DEV_SERVER_URL) void mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL)
  else void mainWindow.loadFile(join(__dirname, '../../renderer/index.html'))
  mainWindow.on('close', (event) => { if (!quitting) { event.preventDefault(); mainWindow?.hide() } })
}

function createTray(): void {
  const icon = process.platform === 'win32' ? join(__dirname, '../../../resources/icon.ico') : join(__dirname, '../../../resources/icon.png')
  try { tray = new Tray(icon); tray.setToolTip('Media Experiment Ledger Studio'); tray.setContextMenu(Menu.buildFromTemplate([{ label: 'Open Studio', click: () => mainWindow?.show() }, { type: 'separator' }, { label: 'Quit', click: () => { quitting = true; app.quit() } }])) } catch { tray = null }
}

app.whenReady().then(() => {
  session.defaultSession.setPermissionRequestHandler((_webContents, _permission, callback) => callback(false))
  const db = new StudioDatabase(join(app.getPath('userData'), 'studio.sqlite'))
  registerIpc(db, new JobManager(db))
  createWindow(); createTray()
  app.on('activate', () => mainWindow ? mainWindow.show() : createWindow())
})
app.on('before-quit', () => { quitting = true })
app.on('window-all-closed', () => { if (process.platform !== 'darwin' && !tray) app.quit() })
