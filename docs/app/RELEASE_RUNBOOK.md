# Media Experiment Ledger Studio Release Runbook

This runbook is normative for the `studio-v*` application Release family. It complements `app-product-contract.json`, the v1 acceptance matrix and the TDD/SDD policy.

## Release entry points

The reusable release implementation is `.github/workflows/app-release-core.yml` on `app-main`.

Two callers are supported:

1. a push to `app-main` that changes `app/release-request.json`;
2. a manual workflow dispatcher on the repository default branch.

Both callers use the same release core, package matrix, evidence checks and collision policy.

## Release request

`app/release-request.json` is schema-versioned and records:

- requested version or `auto`;
- release channel: `alpha`, `beta` or `stable`;
- Markdown summary;
- features/fixes as an array, comma-separated string or newline-separated string;
- compatible Quick Start and Full Research corpus tags;
- whether to create a GitHub Release;
- whether the verified Release remains draft.

Feature strings are normalized, deduplicated and rendered as Markdown bullets.

## Version and tag policy

Tags use `studio-v<semver>`.

- `auto` with `alpha` or `beta` selects the next unused `<package-version>-<channel>.N`.
- `auto` with `stable` uses the package version when free, otherwise advances the patch component until an unused tag is found.
- an explicitly requested tag that already exists is release-blocking;
- an existing Release is never edited, replaced or uploaded with `--clobber`;
- the version resolver reads all existing `studio-v*` tags before the build matrix begins.

## Immutable source policy

The preflight job resolves the requested source ref to one commit SHA. Every Windows, Linux and macOS build checks out that exact SHA. Release notes, manifests and the GitHub Release tag all record or target the same SHA.

No build job is allowed to independently resolve a moving branch head.

## Required package matrix

A Release is blocked unless all eight application packages exist:

- Windows x64 NSIS installer;
- Windows x64 portable executable;
- macOS arm64 DMG;
- macOS arm64 update ZIP;
- macOS Intel x64 DMG;
- macOS Intel x64 update ZIP;
- Linux x64 AppImage;
- Linux x64 `.deb`.

The verifier also requires four engine build manifests and four successful packaged-application smoke records: Windows x64, Linux x64, macOS arm64 and macOS x64.

## Validation performed by every release build

Each platform job performs:

1. locked `npm ci` installation;
2. production dependency audit;
3. TypeScript and Vue typecheck;
4. JavaScript tests and coverage gates;
5. Python engine tests;
6. release-tool unit tests;
7. self-contained PyInstaller engine build;
8. renderer/main/preload production build;
9. platform package generation;
10. real packaged-application launch with sandboxed preload, SQLite and engine checks;
11. engine, package and launch-evidence collection.

The finalizer generates:

- `RELEASE_NOTES.md`;
- `SHA256SUMS`;
- optional `SHA256SUMS.asc`;
- `release-manifest.json`;
- `release-verification.json`;
- CycloneDX SBOM;
- third-party notices;
- per-platform engine and launch evidence.

## Publication transaction

Publication is deliberately two-phase:

1. create a private draft Release at the unused tag;
2. upload the complete verified asset set without clobbering;
3. leave the Release as a draft when requested;
4. otherwise publish only after upload succeeds.

A failed upload leaves a private draft rather than a visible incomplete Release.

## Date policy

Release notes use the calendar date in `Asia/Taipei`. The release plan and manifest also retain UTC timestamps. Neither representation replaces the other.

## Channel and signing policy

### Alpha / beta

Prereleases may be unsigned. Release notes must state that Windows or macOS can display publisher warnings and instruct users to verify `SHA256SUMS`. A detached GPG checksum signature is included when keys are configured but is not falsely claimed when absent.

### Stable

Stable publication is blocked without:

- Windows signing certificate and valid Authenticode verification;
- Apple Developer ID signing credentials;
- Apple notarization and Gatekeeper assessment;
- GPG checksum signing key;
- the remaining real DirectML, CUDA and CoreML hardware evidence;
- required sample-corpus redistribution/privacy attestations;
- manual large-corpus and release acceptance evidence.

Unsigned output must never be relabeled as stable.

## Corpus policy

Quick Start and Full Research corpora are immutable independent Release families. The app Release records compatible corpus tags but does not silently duplicate large corpus assets. Unknown data or model redistribution rights remain `do_not_distribute`.

## Cleanup and retention

The finalizer removes temporary staging directories with an `always()` cleanup step after artifacts and Releases are handled. GitHub Actions build evidence uses bounded retention. Source datasets remain governed by their own immutable Release and local-storage policies.

## Recovery

When a release fails:

- do not reuse or overwrite an existing public tag;
- inspect the failed job and uploaded diagnostics;
- fix the source on a feature branch from `app-main`;
- merge normally, retaining the branch;
- edit the release request to trigger a new collision-safe prerelease sequence;
- delete an incomplete private draft only after confirming no useful evidence is lost.
