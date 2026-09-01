import { ipcMain } from 'electron'
import { z } from 'zod'
import { DIAGNOSTICS_IPC } from '../shared/diagnostics-contracts'
import type { SupportManager } from './support-manager'

export function registerDiagnosticsIpc(support: SupportManager): void {
  ipcMain.handle(DIAGNOSTICS_IPC.preview, () => support.preview())
  ipcMain.handle(DIAGNOSTICS_IPC.createBundle, (_event, outputDirectory: string) =>
    support.createBundle(z.string().min(1).max(32768).parse(outputDirectory)))
  ipcMain.handle(DIAGNOSTICS_IPC.consentGet, () => support.consent())
  ipcMain.handle(DIAGNOSTICS_IPC.consentSet, (_event, enabled: boolean, endpoint: string) =>
    support.setConsent(z.boolean().parse(enabled), z.string().max(4096).parse(endpoint)))
  ipcMain.handle(DIAGNOSTICS_IPC.send, () => support.send())
}
