import { readFileSync, statSync } from 'node:fs'
import { basename, resolve } from 'node:path'
import type {
  GitHubPublishRequest,
  GitHubPublishResult,
} from '../shared/integration-contracts'
import { SecretStore } from './secret-store'

type FetchLike = typeof fetch

interface GitHubReleaseResponse {
  id: number
  html_url: string
  upload_url: string
  draft: boolean
  prerelease: boolean
  tag_name: string
}

function parseRepository(value: string): { owner: string; repo: string } {
  const match = /^([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))\/([A-Za-z0-9._-]{1,100})$/u.exec(value.trim())
  if (!match) throw new Error('Repository must use the owner/name format.')
  return { owner: match[1]!, repo: match[2]! }
}

function validTag(tag: string): boolean {
  if (!tag || tag.length > 200 || tag.startsWith('-') || tag.endsWith('.') || tag.includes('..') || tag.includes('@{')) return false
  const forbidden = [' ', '\t', '\r', '\n', '~', '^', ':', '?', '*', '[', ']', '\\']
  return forbidden.every(character => !tag.includes(character)) && !/[\u0000-\u001f\u007f]/u.test(tag)
}

function safeAssetName(path: string): string {
  const name = basename(path)
  if (!name || name === '.' || name === '..' || /[\u0000-\u001f\u007f]/u.test(name)) throw new Error('Release asset name is invalid.')
  return name
}

export class GitHubReleasePublisher {
  constructor(
    private readonly secrets: SecretStore,
    private readonly fetchImpl: FetchLike = fetch,
  ) {}

  async publish(request: GitHubPublishRequest): Promise<GitHubPublishResult> {
    const { owner, repo } = parseRepository(request.repository)
    const environment = await this.secrets.resolveEnvironment(request.credentialProfileId)
    const token = Object.values(environment)[0]
    if (!token) throw new Error('GitHub credential profile did not resolve a token.')

    const tag = request.tag.trim()
    if (!validTag(tag)) throw new Error('Release tag is invalid.')
    const paths = request.assetPaths.map(path => resolve(path))
    const assetNames = paths.map(safeAssetName)
    if (new Set(assetNames).size !== assetNames.length) throw new Error('Release asset file names must be unique.')
    for (const path of paths) {
      const stat = statSync(path)
      if (!stat.isFile()) throw new Error(`Release asset is not a file: ${safeAssetName(path)}`)
      if (stat.size <= 0) throw new Error(`Release asset is empty: ${safeAssetName(path)}`)
    }

    const api = `https://api.github.com/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}`
    const existing = await this.fetchImpl(`${api}/releases/tags/${encodeURIComponent(tag)}`, {
      headers: this.headers(token),
      redirect: 'error',
    })
    if (existing.ok) throw new Error(`Release tag already exists and will not be modified: ${tag}`)
    if (existing.status !== 404) await this.throwResponse('Unable to verify release tag availability', existing)

    const created = await this.json<GitHubReleaseResponse>(`${api}/releases`, token, {
      method: 'POST',
      body: JSON.stringify({
        tag_name: tag,
        name: request.name.trim(),
        body: request.body,
        draft: true,
        prerelease: request.prerelease,
        generate_release_notes: false,
      }),
    })

    const uploadBase = created.upload_url.replace(/\{\?name,label\}$/u, '')
    const uploadedAssets: Array<{ name: string; sizeBytes: number }> = []
    for (let index = 0; index < paths.length; index += 1) {
      const path = paths[index]!
      const name = assetNames[index]!
      const bytes = readFileSync(path)
      const response = await this.fetchImpl(`${uploadBase}?name=${encodeURIComponent(name)}`, {
        method: 'POST',
        headers: {
          ...this.headers(token),
          'Content-Type': 'application/octet-stream',
          'Content-Length': String(bytes.byteLength),
        },
        body: bytes,
        redirect: 'error',
      })
      if (!response.ok) await this.throwResponse(`Failed to upload ${name}`, response)
      uploadedAssets.push({ name, sizeBytes: bytes.byteLength })
    }

    let finalRelease = created
    if (!request.draft) {
      finalRelease = await this.json<GitHubReleaseResponse>(`${api}/releases/${created.id}`, token, {
        method: 'PATCH',
        body: JSON.stringify({ draft: false, prerelease: request.prerelease }),
      })
    }
    return {
      releaseId: finalRelease.id,
      htmlUrl: finalRelease.html_url,
      tag: finalRelease.tag_name,
      uploadedAssets,
      draft: finalRelease.draft,
      prerelease: finalRelease.prerelease,
    }
  }

  private headers(token: string): Record<string, string> {
    return {
      Accept: 'application/vnd.github+json',
      Authorization: `Bearer ${token}`,
      'User-Agent': 'Media-Experiment-Ledger-Studio',
      'X-GitHub-Api-Version': '2022-11-28',
      'Content-Type': 'application/json',
    }
  }

  private async json<T>(url: string, token: string, init: RequestInit): Promise<T> {
    const response = await this.fetchImpl(url, {
      ...init,
      headers: { ...this.headers(token), ...(init.headers ?? {}) },
      redirect: 'error',
    })
    if (!response.ok) await this.throwResponse('GitHub API request failed', response)
    return await response.json() as T
  }

  private async throwResponse(prefix: string, response: Response): Promise<never> {
    const detail = (await response.text()).replaceAll(/[\r\n]+/gu, ' ').slice(0, 500)
    throw new Error(`${prefix} (${response.status}): ${detail || response.statusText}`)
  }
}
