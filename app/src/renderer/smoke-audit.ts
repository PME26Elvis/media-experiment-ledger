import { nextTick } from 'vue'
import type { Router } from 'vue-router'
import { localizedRouteMarker } from './literal-i18n'

export const SMOKE_LOCALES = ['zh-TW', 'en', 'zh-CN', 'ja', 'ko'] as const
export type SmokeLocale = typeof SMOKE_LOCALES[number]

interface SmokeLocaleController {
  global: {
    locale: { value: string }
  }
}

export interface RendererSmokeCheck {
  route: string
  locale: SmokeLocale
  viewport: string
  currentRoute: string
  rendered: boolean
  horizontalOverflow: boolean
  unnamedInteractive: string[]
  leakedTranslationKeys: string[]
  localizedMarker: string
  localizedMarkerFound: boolean
  errorCount: number
  domSummary?: string
  passed: boolean
}

export interface RendererSmokeApi {
  routes(): string[]
  auditAll(viewport: string): Promise<RendererSmokeCheck[]>
  errors(): string[]
}

const capturedErrors: string[] = []

function stringifyConsoleValue(value: unknown): string {
  if (value instanceof Error) return value.stack ?? value.message
  if (typeof value === 'string') return value
  try { return JSON.stringify(value) } catch { return String(value) }
}

function describeElement(element: Element): string {
  const id = element.getAttribute('id')
  const role = element.getAttribute('role')
  const type = element.getAttribute('type')
  return [element.tagName.toLowerCase(), id ? `#${id}` : '', role ? `[role=${role}]` : '', type ? `[type=${type}]` : ''].join('')
}

function labelledByText(element: Element): string {
  const labelledBy = element.getAttribute('aria-labelledby')
  if (!labelledBy) return ''
  return labelledBy.split(/\s+/u)
    .map(id => document.getElementById(id)?.textContent?.trim() ?? '')
    .filter(Boolean)
    .join(' ')
}

function associatedLabelText(element: Element): string {
  if (!(element instanceof HTMLInputElement || element instanceof HTMLSelectElement || element instanceof HTMLTextAreaElement)) return ''
  return [...(element.labels ?? [])].map(label => label.textContent?.trim() ?? '').filter(Boolean).join(' ')
}

function accessibleName(element: Element): string {
  return [
    element.getAttribute('aria-label') ?? '',
    labelledByText(element),
    associatedLabelText(element),
    element.getAttribute('title') ?? '',
    element.getAttribute('placeholder') ?? '',
    element.textContent?.trim() ?? '',
  ].find(value => value.length > 0) ?? ''
}

function isVisible(element: Element): boolean {
  if (!(element instanceof HTMLElement)) return false
  if (element.hidden || element.getAttribute('aria-hidden') === 'true') return false
  const style = getComputedStyle(element)
  return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0' && element.getClientRects().length > 0
}

function unnamedInteractiveElements(): string[] {
  const selector = [
    'button', 'a[href]', 'input:not([type="hidden"])', 'select', 'textarea',
    '[role="button"]', '[role="link"]', '[role="checkbox"]', '[role="switch"]',
    '[tabindex]:not([tabindex="-1"])',
  ].join(',')
  return [...document.querySelectorAll(selector)]
    .filter(isVisible)
    .filter(element => accessibleName(element).length === 0)
    .map(describeElement)
    .slice(0, 50)
}

function leakedTranslationKeys(): string[] {
  const text = document.body.textContent ?? ''
  return [...new Set(text.match(/\b(?:app|nav|common|integrations|workspace|import|samples|automation|atlas|detection|jobs|models|reports|updates|diagnostics|settings)\.[a-z][a-zA-Z0-9_.-]*/gu) ?? [])].sort()
}

function animationFrame(): Promise<void> {
  return new Promise(resolve => requestAnimationFrame(() => resolve()))
}

async function waitForRouteRoot(timeoutMs = 2000): Promise<boolean> {
  const deadline = performance.now() + timeoutMs
  await nextTick()
  while (performance.now() < deadline) {
    if (document.querySelector('.page-wrap')) {
      await animationFrame()
      await animationFrame()
      return Boolean(document.querySelector('.page-wrap'))
    }
    await new Promise(resolve => setTimeout(resolve, 25))
  }
  return false
}

function domSummary(): string {
  const main = document.querySelector('main')
  const source = main?.innerHTML ?? document.body.innerHTML
  return source.replaceAll(/\s+/gu, ' ').slice(0, 3000)
}

export function installSmokeAudit(router: Router, i18n: SmokeLocaleController): void {
  if (new URLSearchParams(window.location.search).get('mel-smoke') !== '1') return

  const originalConsoleError = console.error.bind(console)
  console.error = (...values: unknown[]) => {
    capturedErrors.push(`[console.error] ${values.map(stringifyConsoleValue).join(' ')}`)
    originalConsoleError(...values)
  }
  window.addEventListener('error', event => {
    capturedErrors.push(event.error instanceof Error ? event.error.stack ?? event.error.message : event.message)
  })
  window.addEventListener('unhandledrejection', event => {
    capturedErrors.push(event.reason instanceof Error ? event.reason.stack ?? event.reason.message : String(event.reason))
  })

  const api: RendererSmokeApi = {
    routes: () => [...new Set(router.getRoutes()
      .filter(route => route.name && !String(route.path).includes(':'))
      .map(route => route.path)
      .filter(path => path !== '/'))].sort(),
    errors: () => [...capturedErrors],
    auditAll: async viewport => {
      const checks: RendererSmokeCheck[] = []
      for (const locale of SMOKE_LOCALES) {
        for (const route of api.routes()) {
          const errorStart = capturedErrors.length
          await router.push(route)
          i18n.global.locale.value = locale
          const rendered = await waitForRouteRoot()
          const documentWidth = document.documentElement.scrollWidth
          const viewportWidth = document.documentElement.clientWidth
          const unnamedInteractive = unnamedInteractiveElements()
          const translationKeys = leakedTranslationKeys()
          const horizontalOverflow = documentWidth > viewportWidth + 2
          const errorCount = capturedErrors.length - errorStart
          const localizedMarker = localizedRouteMarker(route, locale)
          const localizedMarkerFound = localizedMarker.length > 0 && (document.querySelector('.page-wrap')?.textContent ?? '').includes(localizedMarker)
          checks.push({
            route,
            locale,
            viewport,
            currentRoute: router.currentRoute.value.fullPath,
            rendered,
            horizontalOverflow,
            unnamedInteractive,
            leakedTranslationKeys: translationKeys,
            localizedMarker,
            localizedMarkerFound,
            errorCount,
            domSummary: rendered && localizedMarkerFound ? undefined : domSummary(),
            passed: rendered && !horizontalOverflow && unnamedInteractive.length === 0 && translationKeys.length === 0 && localizedMarkerFound && errorCount === 0,
          })
        }
      }
      return checks
    },
  }
  Object.defineProperty(window, '__melSmoke', { value: Object.freeze(api), enumerable: false, configurable: false })
}
