import { translateLiteral } from './literal-i18n'

const routeTitles: Record<string, string> = {
  '/workspace': 'Your media intelligence workspace',
  '/import': 'Bring large corpora under control',
  '/samples': 'Run the product before supplying your own data',
  '/automation': 'Rate-conscious generation orchestration',
  '/atlas': 'Evidence first. Presentation second.',
  '/detection': 'Multi-model inference with durable checkpoints',
  '/jobs': 'Job Center',
  '/models': 'Verified model registry',
  '/reports': 'Turn immutable evidence into a polished document',
  '/updates': 'Verified upgrades with a way back',
  '/diagnostics': 'Preview every byte before it leaves',
  '/settings': 'Settings',
}

const explicitMarkers: Record<string, Record<string, string>> = {
  '/integrations': {
    en: 'Integration Center',
    'zh-TW': '整合中心',
    'zh-CN': '集成中心',
    ja: '連携センター',
    ko: '통합 센터',
  },
}

export function localizedRouteMarker(route: string, locale: string): string {
  const explicit = explicitMarkers[route]?.[locale]
  if (explicit) return explicit
  const source = routeTitles[route]
  return source ? translateLiteral(locale, source) : ''
}
