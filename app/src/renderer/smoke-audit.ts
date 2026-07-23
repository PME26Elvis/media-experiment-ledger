import { nextTick } from 'vue'
import type { I18n } from 'vue-i18n'
import type { Router } from 'vue-router'

export const SMOKE_LOCALES = ['zh-TW', 'en', 'zh-CN', 'ja', 'ko'] as const
export type SmokeLocale = typeof SMOKE_LOCALES[number]

export interface RendererSmokeCheck {
  route: string
  locale: SmokeLocale
  viewport: string
  rendered: boolean
  horizontalOverflow: boolean
  unnamedInteractive: string[]
  leakedTranslationKeys: string[]
  errorCount: number
  passed: boolean
}

export interface RendererSmokeApi {
  routes(): string[]
  auditAll(viewport: string): Promise<RendererSmokeCheck[]>
  errors(): string[]
}

const capturedErrors: string[] = []

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

async function settle(): Promise<void> {
  await nextTick()
  await new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
}

export function installSmokeAudit(router: Router, i18n: I18n): void {
  if (new URLSearchParams(window.location.search).get('mel-smoke') !== '1') return

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
          ;(i18n.global.locale as { value: string }).value = locale
          await settle()
          const documentWidth = document.documentElement.scrollWidth
          const viewportWidth = document.documentElement.clientWidth
          const unnamedInteractive = unnamedInteractiveElements()
          const translationKeys = leakedTranslationKeys()
          const rendered = Boolean(document.querySelector('.page-wrap'))
          const horizontalOverflow = documentWidth > viewportWidth + 2
          const errorCount = capturedErrors.length - errorStart
          checks.push({
            route,
            locale,
            viewport,
            rendered,
            horizontalOverflow,
            unnamedInteractive,
            leakedTranslationKeys: translationKeys,
            errorCount,
            passed: rendered && !horizontalOverflow && unnamedInteractive.length === 0 && translationKeys.length === 0 && errorCount === 0,
          })
        }
      }
      return checks
    },
  }
  Object.defineProperty(window, '__melSmoke', { value: Object.freeze(api), enumerable: false, configurable: false })
}
