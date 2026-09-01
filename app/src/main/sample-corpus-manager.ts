import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync,
  renameSync,
} from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import type {
  JobRecord,
  SampleCorpusManifest,
  SampleCorpusStatus,
} from '../shared/contracts'
import { validateSampleCorpusManifest } from '../shared/sample-corpus-schema'
import { JobManager } from './job-manager'

function atomicJson(path: string, value: unknown): void {
  mkdirSync(dirname(path), { recursive: true })
  const temporary = `${path}.tmp`
  writeFileSync(temporary, JSON.stringify(value, null, 2), 'utf8')
  renameSync(temporary, path)
}

function verifiedReceipt(
  path: string,
  asset: { sha256: string; sizeBytes: number },
): boolean {
  try {
    const receipt = JSON.parse(
      readFileSync(`${path}.verified.json`, 'utf8'),
    ) as { sha256?: string; size?: number }
    return existsSync(path)
      && statSync(path).size === asset.sizeBytes
      && receipt.sha256 === asset.sha256
      && receipt.size === asset.sizeBytes
  } catch {
    return false
  }
}

export class SampleCorpusManager {
  private readonly root: string
  private readonly manifestsRoot: string

  constructor(userDataPath: string, private readonly jobs: JobManager) {
    this.root = join(userDataPath, 'sample-corpora')
    this.manifestsRoot = join(this.root, 'manifests')
    mkdirSync(this.manifestsRoot, { recursive: true })
  }

  list(): SampleCorpusStatus[] {
    return readdirSync(this.manifestsRoot, { withFileTypes: true })
      .filter((entry) => entry.isFile() && entry.name.endsWith('.json'))
      .map((entry) => validateSampleCorpusManifest(JSON.parse(
        readFileSync(join(this.manifestsRoot, entry.name), 'utf8'),
      )))
      .sort((a, b) => a.tier.localeCompare(b.tier) || b.version - a.version)
      .map((manifest) => this.status(manifest))
  }

  async refreshRemote(): Promise<SampleCorpusStatus[]> {
    const response = await fetch(
      'https://api.github.com/repos/PME26Elvis/media-experiment-ledger/releases?per_page=100',
      {
        headers: {
          Accept: 'application/vnd.github+json',
          'User-Agent': 'Media-Experiment-Ledger-Studio',
        },
      },
    )
    if (!response.ok) {
      throw new Error(`GitHub Release discovery failed: HTTP ${response.status}`)
    }
    const releases = await response.json() as Array<{
      tag_name?: string
      draft?: boolean
      assets?: Array<{ name?: string; browser_download_url?: string }>
    }>
    for (const release of releases) {
      if (release.draft || !release.tag_name?.startsWith('studio-sample-corpus-')) {
        continue
      }
      const asset = release.assets?.find((item) => item.name === 'corpus-manifest.json')
      if (!asset?.browser_download_url) continue
      const manifestResponse = await fetch(asset.browser_download_url, {
        headers: { 'User-Agent': 'Media-Experiment-Ledger-Studio' },
      })
      if (!manifestResponse.ok) continue
      const manifest = validateSampleCorpusManifest(await manifestResponse.json())
      if (manifest.releaseTag !== release.tag_name) {
        throw new Error(`Manifest releaseTag mismatch for ${release.tag_name}`)
      }
      atomicJson(
        join(this.manifestsRoot, `${manifest.id}-v${manifest.version}.json`),
        manifest,
      )
    }
    return this.list()
  }

  importManifest(path: string): SampleCorpusStatus {
    const manifest = validateSampleCorpusManifest(
      JSON.parse(readFileSync(resolve(path), 'utf8')),
    )
    atomicJson(
      join(this.manifestsRoot, `${manifest.id}-v${manifest.version}.json`),
      manifest,
    )
    return this.status(manifest)
  }

  install(corpusId: string): JobRecord[] {
    const status = this.list().find((item) => item.manifest.id === corpusId)
    if (!status) throw new Error('Sample corpus manifest not found.')
    if (status.manifest.rightsStatus !== 'approved') {
      throw new Error('Sample corpus publication rights are not approved.')
    }
    mkdirSync(status.installRoot, { recursive: true })
    return status.manifest.assets
      .filter((asset) => asset.required)
      .filter((asset) => !verifiedReceipt(join(status.installRoot, asset.fileName), asset))
      .map((asset) => this.jobs.create({
        kind: 'sample-download',
        title: `Download ${status.manifest.title} · ${asset.fileName}`,
        config: {
          url: asset.url,
          destination: join(status.installRoot, asset.fileName),
          sha256: asset.sha256,
          size_bytes: asset.sizeBytes,
          corpus_id: status.manifest.id,
          asset_id: asset.id,
        },
      }))
  }

  remove(corpusId: string): boolean {
    const status = this.list().find((item) => item.manifest.id === corpusId)
    if (!status) return false
    rmSync(status.installRoot, { recursive: true, force: true })
    return true
  }

  private status(manifest: SampleCorpusManifest): SampleCorpusStatus {
    const installRoot = join(
      this.root,
      'installed',
      manifest.id,
      `v${manifest.version}`,
    )
    const required = manifest.assets.filter((asset) => asset.required)
    let installedAssets = 0
    let installedBytes = 0
    for (const asset of required) {
      if (verifiedReceipt(join(installRoot, asset.fileName), asset)) {
        installedAssets += 1
        installedBytes += asset.sizeBytes
      }
    }
    const activeJobIds = this.jobs.list()
      .filter((job) => job.kind === 'sample-download')
      .filter((job) => job.config.corpus_id === manifest.id)
      .filter((job) => !['completed', 'cancelled', 'failed'].includes(job.status))
      .map((job) => job.id)
    const totalAssets = required.length
    const totalBytes = required.reduce((sum, asset) => sum + asset.sizeBytes, 0)
    return {
      manifest,
      installedAssets,
      totalAssets,
      installedBytes,
      totalBytes,
      state: manifest.rightsStatus !== 'approved'
        ? 'blocked'
        : installedAssets === 0
          ? 'available'
          : installedAssets >= totalAssets
            ? 'installed'
            : 'partial',
      installRoot,
      activeJobIds,
    }
  }
}
