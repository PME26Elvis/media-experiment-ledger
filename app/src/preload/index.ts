import { contextBridge, ipcRenderer } from 'electron'
import { IPC, type MelDesktopApi } from '../shared/contracts'

const api: MelDesktopApi = {
  systemInfo: () => ipcRenderer.invoke(IPC.systemInfo),
  chooseDirectory: defaultPath => ipcRenderer.invoke(IPC.chooseDirectory, defaultPath),
  chooseFile: options => ipcRenderer.invoke(IPC.chooseFile, options),
  revealPath: path => ipcRenderer.invoke(IPC.revealPath, path),
  settings: {
    get: () => ipcRenderer.invoke(IPC.settingsGet),
    set: patch => ipcRenderer.invoke(IPC.settingsSet, patch),
  },
  jobs: {
    list: () => ipcRenderer.invoke(IPC.jobsList),
    create: request => ipcRenderer.invoke(IPC.jobsCreate, request),
    control: (id, action) => ipcRenderer.invoke(IPC.jobsControl, id, action),
  },
  models: {
    list: () => ipcRenderer.invoke(IPC.modelsList),
    import: (modelId, sourcePath) => ipcRenderer.invoke(IPC.modelsImport, modelId, sourcePath),
    remove: modelId => ipcRenderer.invoke(IPC.modelsRemove, modelId),
  },
  secrets: {
    list: () => ipcRenderer.invoke(IPC.secretsList),
    save: request => ipcRenderer.invoke(IPC.secretsSave, request),
    remove: id => ipcRenderer.invoke(IPC.secretsRemove, id),
    unlock: (id, password) => ipcRenderer.invoke(IPC.secretsUnlock, id, password),
    lock: id => ipcRenderer.invoke(IPC.secretsLock, id),
  },
  corpora: {
    list: () => ipcRenderer.invoke(IPC.corporaList),
    refresh: () => ipcRenderer.invoke(IPC.corporaRefresh),
    import: manifestPath => ipcRenderer.invoke(IPC.corporaImport, manifestPath),
    install: corpusId => ipcRenderer.invoke(IPC.corporaInstall, corpusId),
    remove: corpusId => ipcRenderer.invoke(IPC.corporaRemove, corpusId),
  },
  reports: {
    list: () => ipcRenderer.invoke(IPC.reportsList),
    create: title => ipcRenderer.invoke(IPC.reportsCreate, title),
    get: id => ipcRenderer.invoke(IPC.reportsGet, id),
    save: (document, checkpoint) => ipcRenderer.invoke(IPC.reportsSave, document, checkpoint),
    delete: id => ipcRenderer.invoke(IPC.reportsDelete, id),
    importAtlas: manifestPath => ipcRenderer.invoke(IPC.reportsImportAtlas, manifestPath),
    exportPdf: (id, outputDirectory) => ipcRenderer.invoke(IPC.reportsExportPdf, id, outputDirectory),
    revisions: id => ipcRenderer.invoke(IPC.reportsRevisions, id),
    restore: (id, revisionPath) => ipcRenderer.invoke(IPC.reportsRestore, id, revisionPath),
  },
  recovery: {
    list: () => ipcRenderer.invoke(IPC.recoveryList),
    create: reason => ipcRenderer.invoke(IPC.recoveryCreate, reason),
    restore: id => ipcRenderer.invoke(IPC.recoveryRestore, id),
    remove: id => ipcRenderer.invoke(IPC.recoveryRemove, id),
    integrity: () => ipcRenderer.invoke(IPC.recoveryIntegrity),
  },
  updater: {
    status: () => ipcRenderer.invoke(IPC.updaterStatus),
    check: () => ipcRenderer.invoke(IPC.updaterCheck),
    download: () => ipcRenderer.invoke(IPC.updaterDownload),
    install: () => ipcRenderer.invoke(IPC.updaterInstall),
    importOffline: (manifestPath, packagePath) => ipcRenderer.invoke(IPC.updaterImportOffline, manifestPath, packagePath),
    openOffline: () => ipcRenderer.invoke(IPC.updaterOpenOffline),
  },
}

contextBridge.exposeInMainWorld('mel', Object.freeze(api))
