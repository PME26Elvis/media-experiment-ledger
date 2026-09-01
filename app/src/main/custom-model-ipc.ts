import { ipcMain } from 'electron'
import { z } from 'zod'
import { CUSTOM_MODEL_IPC } from '../shared/custom-model-contracts'
import type { CustomModelManager } from './custom-model-manager'

export function registerCustomModelIpc(models: CustomModelManager): void {
  ipcMain.handle(CUSTOM_MODEL_IPC.list, () => models.list())
  ipcMain.handle(CUSTOM_MODEL_IPC.import, (_event, manifestPath: string) =>
    models.import(z.string().min(1).max(32768).parse(manifestPath)))
  ipcMain.handle(CUSTOM_MODEL_IPC.remove, (_event, modelId: string) =>
    models.remove(z.string().min(1).max(100).parse(modelId)))
}
