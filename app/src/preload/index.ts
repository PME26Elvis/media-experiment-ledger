import { contextBridge, ipcRenderer } from 'electron'
import type { MelDesktopApi } from '../shared/contracts'
import type { CustomModelApi } from '../shared/custom-model-contracts'
import type { DiagnosticsApi } from '../shared/diagnostics-contracts'
import type { IntegrationApi } from '../shared/integration-contracts'
import type { ReportTemplateApi } from '../shared/template-contracts'

// A sandboxed Electron preload may not load arbitrary relative CommonJS modules.
// Keep the runtime dependency surface limited to `electron`, while TypeScript verifies
// these local channel maps against the canonical shared contracts at build time.
const IPC = {
  systemInfo: 'mel:system-info',
  chooseDirectory: 'mel:choose-directory',
  chooseFile: 'mel:choose-file',
  revealPath: 'mel:reveal-path',
  settingsGet: 'mel:settings-get',
  settingsSet: 'mel:settings-set',
  jobsList: 'mel:jobs-list',
  jobsCreate: 'mel:jobs-create',
  jobsControl: 'mel:jobs-control',
  modelsList: 'mel:models-list',
  modelsImport: 'mel:models-import',
  modelsRemove: 'mel:models-remove',
  secretsList: 'mel:secrets-list',
  secretsSave: 'mel:secrets-save',
  secretsRemove: 'mel:secrets-remove',
  secretsUnlock: 'mel:secrets-unlock',
  secretsLock: 'mel:secrets-lock',
  corporaList: 'mel:corpora-list',
  corporaRefresh: 'mel:corpora-refresh',
  corporaImport: 'mel:corpora-import',
  corporaInstall: 'mel:corpora-install',
  corporaRemove: 'mel:corpora-remove',
  reportsList: 'mel:reports-list',
  reportsCreate: 'mel:reports-create',
  reportsGet: 'mel:reports-get',
  reportsSave: 'mel:reports-save',
  reportsDelete: 'mel:reports-delete',
  reportsImportAtlas: 'mel:reports-import-atlas',
  reportsExportPdf: 'mel:reports-export-pdf',
  reportsRevisions: 'mel:reports-revisions',
  reportsRestore: 'mel:reports-restore',
  recoveryList: 'mel:recovery-list',
  recoveryCreate: 'mel:recovery-create',
  recoveryRestore: 'mel:recovery-restore',
  recoveryRemove: 'mel:recovery-remove',
  recoveryIntegrity: 'mel:recovery-integrity',
  updaterStatus: 'mel:updater-status',
  updaterCheck: 'mel:updater-check',
  updaterDownload: 'mel:updater-download',
  updaterInstall: 'mel:updater-install',
  updaterImportOffline: 'mel:updater-import-offline',
  updaterOpenOffline: 'mel:updater-open-offline',
} as const satisfies typeof import('../shared/contracts').IPC

const DIAGNOSTICS_IPC = {
  preview: 'mel:diagnostics-preview',
  createBundle: 'mel:diagnostics-create-bundle',
  consentGet: 'mel:telemetry-consent-get',
  consentSet: 'mel:telemetry-consent-set',
  send: 'mel:telemetry-send',
} as const satisfies typeof import('../shared/diagnostics-contracts').DIAGNOSTICS_IPC

const TEMPLATE_IPC = {
  list: 'mel:templates-list',
  import: 'mel:templates-import',
  export: 'mel:templates-export',
  remove: 'mel:templates-remove',
  apply: 'mel:templates-apply',
  applied: 'mel:templates-applied',
} as const satisfies typeof import('../shared/template-contracts').TEMPLATE_IPC

const CUSTOM_MODEL_IPC = {
  list: 'mel:custom-model-list',
  import: 'mel:custom-model-import',
  remove: 'mel:custom-model-remove',
} as const satisfies typeof import('../shared/custom-model-contracts').CUSTOM_MODEL_IPC

const INTEGRATION_IPC = {
  schedulesList: 'mel:integrations-schedules-list',
  schedulesSave: 'mel:integrations-schedules-save',
  schedulesRemove: 'mel:integrations-schedules-remove',
  schedulesRunNow: 'mel:integrations-schedules-run-now',
  schedulesPreview: 'mel:integrations-schedules-preview',
  syncRun: 'mel:integrations-sync-run',
  githubPublish: 'mel:integrations-github-publish',
  wasmPostprocess: 'mel:integrations-wasm-postprocess',
} as const satisfies typeof import('../shared/integration-contracts').INTEGRATION_IPC

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

const diagnostics: DiagnosticsApi = {
  preview: () => ipcRenderer.invoke(DIAGNOSTICS_IPC.preview),
  createBundle: outputDirectory => ipcRenderer.invoke(DIAGNOSTICS_IPC.createBundle, outputDirectory),
  consent: {
    get: () => ipcRenderer.invoke(DIAGNOSTICS_IPC.consentGet),
    set: (enabled, endpoint) => ipcRenderer.invoke(DIAGNOSTICS_IPC.consentSet, enabled, endpoint),
  },
  send: () => ipcRenderer.invoke(DIAGNOSTICS_IPC.send),
}

const templates: ReportTemplateApi = {
  list: () => ipcRenderer.invoke(TEMPLATE_IPC.list),
  import: path => ipcRenderer.invoke(TEMPLATE_IPC.import, path),
  export: (id, outputDirectory) => ipcRenderer.invoke(TEMPLATE_IPC.export, id, outputDirectory),
  remove: id => ipcRenderer.invoke(TEMPLATE_IPC.remove, id),
  apply: (documentId, templateId) => ipcRenderer.invoke(TEMPLATE_IPC.apply, documentId, templateId),
  applied: documentId => ipcRenderer.invoke(TEMPLATE_IPC.applied, documentId),
}

const customModels: CustomModelApi = {
  list: () => ipcRenderer.invoke(CUSTOM_MODEL_IPC.list),
  import: manifestPath => ipcRenderer.invoke(CUSTOM_MODEL_IPC.import, manifestPath),
  remove: modelId => ipcRenderer.invoke(CUSTOM_MODEL_IPC.remove, modelId),
}

const integrations: IntegrationApi = {
  schedules: {
    list: () => ipcRenderer.invoke(INTEGRATION_IPC.schedulesList),
    save: request => ipcRenderer.invoke(INTEGRATION_IPC.schedulesSave, request),
    remove: id => ipcRenderer.invoke(INTEGRATION_IPC.schedulesRemove, id),
    runNow: id => ipcRenderer.invoke(INTEGRATION_IPC.schedulesRunNow, id),
    preview: request => ipcRenderer.invoke(INTEGRATION_IPC.schedulesPreview, request),
  },
  sync: {
    run: request => ipcRenderer.invoke(INTEGRATION_IPC.syncRun, request),
  },
  github: {
    publish: request => ipcRenderer.invoke(INTEGRATION_IPC.githubPublish, request),
  },
  wasm: {
    postprocess: request => ipcRenderer.invoke(INTEGRATION_IPC.wasmPostprocess, request),
  },
}

contextBridge.exposeInMainWorld('mel', Object.freeze(api))
contextBridge.exposeInMainWorld('melDiagnostics', Object.freeze(diagnostics))
contextBridge.exposeInMainWorld('melTemplates', Object.freeze(templates))
contextBridge.exposeInMainWorld('melCustomModels', Object.freeze(customModels))
contextBridge.exposeInMainWorld('melIntegrations', Object.freeze(integrations))
