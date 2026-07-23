import { describe, expect, it } from 'vitest'
import {
  PRODUCT_LOCALES,
  catalogEntries,
  localizeTree,
  translateLiteral,
} from '../src/renderer/literal-i18n'
import { localizedRouteMarker } from '../src/renderer/route-localization'

describe('literal product localization', () => {
  it('keeps every exact-match catalog entry complete across supported non-English locales', () => {
    const required = PRODUCT_LOCALES.filter(locale => locale !== 'en')
    for (const [source, translations] of Object.entries(catalogEntries())) {
      expect(source.trim().length).toBeGreaterThan(0)
      for (const locale of required) {
        expect(translations[locale].trim().length, `${source} missing ${locale}`).toBeGreaterThan(0)
      }
    }
  })

  it('provides a locale-specific marker for every packaged route', () => {
    const routes = [
      '/workspace', '/import', '/samples', '/automation', '/atlas', '/detection', '/jobs',
      '/models', '/reports', '/integrations', '/updates', '/diagnostics', '/settings',
    ]
    for (const route of routes) {
      const english = localizedRouteMarker(route, 'en')
      expect(english).not.toBe('')
      for (const locale of PRODUCT_LOCALES.filter(value => value !== 'en')) {
        const translated = localizedRouteMarker(route, locale)
        expect(translated).not.toBe('')
        expect(translated).not.toBe(english)
      }
    }
  })

  it('translates only cataloged product copy and leaves user content unchanged', () => {
    expect(translateLiteral('zh-TW', 'Settings')).toBe('設定')
    expect(translateLiteral('ja', 'Start detection')).toBe('検出を開始')
    expect(translateLiteral('ko', 'my private prompt text')).toBe('my private prompt text')
    expect(translateLiteral('zh-CN', '/Users/example/project')).toBe('/Users/example/project')
  })

  it('supports bounded dynamic product messages without touching arbitrary numbers', () => {
    expect(translateLiteral('zh-TW', 'Discovered 3 approved or reviewable manifests.')).toBe('已找到 3 份已核准或可審核的 manifest。')
    expect(translateLiteral('ko', 'Queued 4 verified part downloads.')).toContain('4')
    expect(translateLiteral('ja', '2026-07-23')).toBe('2026-07-23')
  })

  it('localizes text and accessible attributes, can switch locales, and skips diagnostic or user-owned regions', () => {
    document.body.innerHTML = `
      <main id="root">
        <h1>Settings</h1>
        <button aria-label="Remove">Remove</button>
        <pre>Settings</pre>
        <div data-no-localize>Settings</div>
        <p>my private prompt text</p>
      </main>
    `
    const root = document.querySelector('#root')!
    localizeTree(root, 'zh-TW')
    expect(root.querySelector('h1')?.textContent).toBe('設定')
    expect(root.querySelector('button')?.textContent).toBe('移除')
    expect(root.querySelector('button')?.getAttribute('aria-label')).toBe('移除')
    expect(root.querySelector('pre')?.textContent).toBe('Settings')
    expect(root.querySelector('[data-no-localize]')?.textContent).toBe('Settings')
    expect(root.querySelector('p')?.textContent).toBe('my private prompt text')

    localizeTree(root, 'ja')
    expect(root.querySelector('h1')?.textContent).toBe('設定')
    expect(root.querySelector('button')?.textContent).toBe('削除')

    localizeTree(root, 'en')
    expect(root.querySelector('h1')?.textContent).toBe('Settings')
    expect(root.querySelector('button')?.textContent).toBe('Remove')
  })
})
