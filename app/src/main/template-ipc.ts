import { ipcMain } from 'electron'
import { z } from 'zod'
import { TEMPLATE_IPC } from '../shared/template-contracts'
import type { TemplateManager } from './template-manager'

const pathSchema = z.string().min(1).max(32768)
const uuidSchema = z.string().uuid()

export function registerTemplateIpc(templates: TemplateManager): void {
  ipcMain.handle(TEMPLATE_IPC.list, () => templates.list())
  ipcMain.handle(TEMPLATE_IPC.import, (_event, path: string) => templates.import(pathSchema.parse(path)))
  ipcMain.handle(TEMPLATE_IPC.export, (_event, id: string, outputDirectory: string) =>
    templates.export(z.string().min(1).max(80).parse(id), pathSchema.parse(outputDirectory)))
  ipcMain.handle(TEMPLATE_IPC.remove, (_event, id: string) => templates.remove(z.string().min(1).max(80).parse(id)))
  ipcMain.handle(TEMPLATE_IPC.apply, (_event, documentId: string, templateId: string) =>
    templates.apply(uuidSchema.parse(documentId), z.string().min(1).max(80).parse(templateId)))
  ipcMain.handle(TEMPLATE_IPC.applied, (_event, documentId: string) => templates.applied(uuidSchema.parse(documentId)))
}
