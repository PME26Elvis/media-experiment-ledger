import type { AcceleratorBundleApi } from '../shared/accelerator-bundle-contracts'
import type { MelDesktopApi } from '../shared/contracts'
import type { CustomModelApi } from '../shared/custom-model-contracts'
import type { DetectionWorkflowApi } from '../shared/detection-workflow-contracts'
import type { DiagnosticsApi } from '../shared/diagnostics-contracts'
import type { HardwareApi } from '../shared/hardware-contracts'
import type { IntegrationApi } from '../shared/integration-contracts'
import type { ResourceSchedulerApi } from '../shared/resource-scheduler-contracts'
import type { ReportTemplateApi } from '../shared/template-contracts'
import type { RendererSmokeApi } from './smoke-audit'

declare global {
  interface Window {
    mel: MelDesktopApi
    melHardware: HardwareApi
    melResourceScheduler: ResourceSchedulerApi
    melAcceleratorBundles: AcceleratorBundleApi
    melDetection: DetectionWorkflowApi
    melDiagnostics: DiagnosticsApi
    melTemplates: ReportTemplateApi
    melCustomModels: CustomModelApi
    melIntegrations: IntegrationApi
    __melSmoke?: RendererSmokeApi
  }
}

export {}
