import type { MelDesktopApi } from '../shared/contracts'
import type { DiagnosticsApi } from '../shared/diagnostics-contracts'

declare global {
  interface Window {
    mel: MelDesktopApi
    melDiagnostics: DiagnosticsApi
  }
}

export {}
