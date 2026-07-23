import type { MelDesktopApi } from '../shared/contracts'
import type { CustomModelApi } from '../shared/custom-model-contracts'
import type { DiagnosticsApi } from '../shared/diagnostics-contracts'
import type { IntegrationApi } from '../shared/integration-contracts'
import type { ReportTemplateApi } from '../shared/template-contracts'

declare global {
  interface Window {
    mel: MelDesktopApi
    melDiagnostics: DiagnosticsApi
    melTemplates: ReportTemplateApi
    melCustomModels: CustomModelApi
    melIntegrations: IntegrationApi
  }
}

export {}
