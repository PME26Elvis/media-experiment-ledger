export const TEMPLATE_IPC = {
  list: 'mel:templates-list',
  import: 'mel:templates-import',
  export: 'mel:templates-export',
  remove: 'mel:templates-remove',
  apply: 'mel:templates-apply',
  applied: 'mel:templates-applied',
} as const

export interface ReportTemplateDefinition {
  schemaVersion: 1
  name: string
  description: string
  page: {
    widthInches: number
    heightInches: number
  }
  marginInches: number
  colors: {
    background: string
    surface: string
    text: string
    muted: string
    primary: string
    accent: string
  }
  fontFamily: string
}

export interface CustomReportTemplateSummary {
  id: string
  definition: ReportTemplateDefinition
  createdAt: string
  updatedAt: string
}

export interface AppliedReportTemplate {
  documentId: string
  customTemplateId: string
  definition: ReportTemplateDefinition
  appliedAt: string
}

export interface ReportTemplateApi {
  list(): Promise<CustomReportTemplateSummary[]>
  import(path: string): Promise<CustomReportTemplateSummary>
  export(id: string, outputDirectory: string): Promise<string>
  remove(id: string): Promise<boolean>
  apply(documentId: string, templateId: string): Promise<AppliedReportTemplate>
  applied(documentId: string): Promise<AppliedReportTemplate | null>
}
