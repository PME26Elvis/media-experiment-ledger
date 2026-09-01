import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import { GitHubReleasePublisher } from '../src/main/github-release-publisher'
import { SecretStore } from '../src/main/secret-store'

const roots: string[] = []
function temporaryRoot(): string {
  const root = mkdtempSync(join(tmpdir(), 'mel-github-publisher-'))
  roots.push(root)
  return root
}
afterEach(() => {
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true })
})

describe('GitHubReleasePublisher', () => {
  it('checks tag immutability, creates a draft, uploads assets, then publishes', async () => {
    const root = temporaryRoot()
    const asset = join(root, 'report.pdf')
    writeFileSync(asset, '%PDF-test')
    const secrets = new SecretStore(root)
    const profile = await secrets.save({
      name: 'GitHub test',
      provider: 'github',
      environmentVariable: 'GITHUB_TOKEN',
      backend: 'session',
      secret: 'test-token',
    })
    const calls: Array<{ url: string; method: string; body?: string }> = []
    const fakeFetch: typeof fetch = async (input, init) => {
      const url = String(input)
      const method = init?.method ?? 'GET'
      calls.push({ url, method, body: typeof init?.body === 'string' ? init.body : undefined })
      if (method === 'GET') return new Response('{}', { status: 404 })
      if (url.endsWith('/releases') && method === 'POST') {
        return Response.json({
          id: 42,
          html_url: 'https://github.com/example/project/releases/tag/v1.0.0',
          upload_url: 'https://uploads.github.com/repos/example/project/releases/42/assets{?name,label}',
          draft: true,
          prerelease: false,
          tag_name: 'v1.0.0',
        }, { status: 201 })
      }
      if (url.includes('uploads.github.com')) return Response.json({ id: 7 }, { status: 201 })
      if (url.endsWith('/releases/42') && method === 'PATCH') {
        return Response.json({
          id: 42,
          html_url: 'https://github.com/example/project/releases/tag/v1.0.0',
          upload_url: '',
          draft: false,
          prerelease: false,
          tag_name: 'v1.0.0',
        })
      }
      return new Response('unexpected', { status: 500 })
    }

    const result = await new GitHubReleasePublisher(secrets, fakeFetch).publish({
      repository: 'example/project',
      tag: 'v1.0.0',
      name: 'Stable 1.0.0',
      body: 'Release body',
      draft: false,
      prerelease: false,
      assetPaths: [asset],
      credentialProfileId: profile.id,
    })

    expect(result).toMatchObject({ releaseId: 42, draft: false, tag: 'v1.0.0' })
    expect(result.uploadedAssets).toEqual([{ name: 'report.pdf', sizeBytes: 9 }])
    expect(calls.map(call => call.method)).toEqual(['GET', 'POST', 'POST', 'PATCH'])
    expect(JSON.parse(calls[1]!.body!)).toMatchObject({ draft: true, tag_name: 'v1.0.0' })
    expect(JSON.parse(calls[3]!.body!)).toEqual({ draft: false, prerelease: false })
    expect(calls.some(call => call.body?.includes('test-token'))).toBe(false)
  })

  it('refuses to overwrite an existing tag', async () => {
    const root = temporaryRoot()
    const asset = join(root, 'asset.txt')
    writeFileSync(asset, 'content')
    const secrets = new SecretStore(root)
    const profile = await secrets.save({ name: 'GitHub', provider: 'github', environmentVariable: 'GITHUB_TOKEN', backend: 'session', secret: 'token' })
    const existingFetch: typeof fetch = async () => Response.json({ id: 1 })
    await expect(new GitHubReleasePublisher(secrets, existingFetch).publish({
      repository: 'example/project', tag: 'v1', name: 'v1', body: '', draft: true, prerelease: true,
      assetPaths: [asset], credentialProfileId: profile.id,
    })).rejects.toThrow(/already exists/u)
  })
})
