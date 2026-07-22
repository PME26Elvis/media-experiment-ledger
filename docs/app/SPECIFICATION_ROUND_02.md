# Specification Round 02 — Accepted Product Decisions

> Status: **normative amendment**  
> Accepted: 2026-07-22  
> Applies to: `app-main`  
> Contract version: `2026-07-22.2`

This document records the user's answers to the first product-definition review round. It is normative and takes precedence over conflicting provisional language in the original baseline documents until those documents are consolidated before implementation begins.

## 1. Public product identity

### Decision

The public product name is:

> **Media Experiment Ledger Studio**

Descriptor:

> **Atlas · Detection · Media Automation**

Canonical identifiers:

- slug: `media-experiment-ledger-studio`;
- application ID: `io.github.pme26elvis.media-experiment-ledger-studio`;
- app Release prefix: `studio-v`;
- executable/product file name SHOULD use the full name or a filesystem-safe derivative;
- `MEL Studio` MUST NOT be the sole public brand because unrelated software already uses that short name.

### Branding constraints

- The application MUST NOT use Electron, Vue, Vuetify, Agnes, YOLOX, NanoDet, COCO or other third-party names/logos as its own product branding.
- Third-party names MAY appear descriptively in provider/model cards and notices.
- Before the first stable signed release, the maintainer SHOULD perform a practical trademark/name collision review for the exact product name and app-store categories used. This is not a guarantee of trademark clearance.

## 2. Required first-stable platform and package matrix

All listed targets are v1 requirements rather than optional stretch goals:

| Platform | Architecture | Required artifact | Update behavior |
|---|---|---|---|
| Windows | x64 | NSIS installer | signed online update and offline installer import |
| Windows | x64 | portable executable/package | guided replace-and-relaunch; shared user-data directory preserved |
| macOS | arm64 | signed/notarized DMG plus update ZIP | online update and offline DMG import |
| macOS | x64 | signed/notarized DMG plus update ZIP | online update and offline DMG import |
| Linux | x64 | AppImage | online update where validated; guided replacement fallback |
| Linux | x64 | `.deb` | updater/package-manager-aware flow plus guided package replacement |

A universal macOS artifact MAY be added when size, signing, notarization and update testing are acceptable, but separate arm64 and x64 support remains the acceptance requirement.

No target is considered supported merely because a file was produced. Each artifact requires clean-environment install, launch, project migration, update and uninstall/reinstall preservation tests.

## 3. Sample corpus product

Two sample tiers are required.

### 3.1 Quick Start corpus

Purpose:

- fast onboarding;
- modest download size;
- enough images and videos to demonstrate import, thumbnailing, Atlas, PDF authoring and multi-model detection;
- deterministic automated smoke and tutorial fixtures.

The Quick Start corpus SHOULD contain a deliberately selected subset rather than only the first files in chronological order. It should include:

- multiple image cohorts with at least 2, 3, 4 and 5+ samples;
- at least two comparable video cohorts;
- a mixture of aspect ratios and resolutions;
- images that produce both overlapping and disagreeing detector outputs;
- at least one invalid/quarantined fixture kept separate from ordinary onboarding data.

### 3.2 Full Research corpus

Purpose:

- preserve the sanitized canonical corpus at meaningful scale;
- exercise thousands-of-assets architecture as the corpus grows;
- reproduce current Atlas and detector examples;
- support realistic performance and recovery evaluation.

The Full Research corpus MAY be multipart and multi-gigabyte. Users may download only images, only videos or selected parts when the manifest permits.

### 3.3 Release architecture

Sample corpora normally live in dedicated immutable Releases:

```text
studio-sample-corpus-quick-start-v1
studio-sample-corpus-full-research-v1
```

App Releases contain a signed/repository-controlled recommendation manifest that points to compatible corpus tags and manifest hashes. Unchanged corpus bytes MUST NOT be re-uploaded with every app release.

Example assets:

```text
mel-sample-corpus-quick-start-images-v1-part001.zip
mel-sample-corpus-quick-start-videos-v1-part001.zip
mel-sample-corpus-full-research-images-v1-part001.zip
mel-sample-corpus-full-research-videos-v1-part001.zip
mel-sample-corpus-quick-start-manifest-v1.json
mel-sample-corpus-full-research-manifest-v1.json
SHA256SUMS.txt
```

Each part target is below 1.9 GB. The manifest records membership, sizes, hashes, media counts, schema, license/provenance and compatibility.

### 3.4 Publication boundary

Both tiers are public only after automated and manual review for:

- API keys, bearer tokens and credentials;
- signed or temporary URLs;
- local usernames and absolute paths;
- EXIF/device/location metadata;
- personal/private prompt content;
- provider response payloads that are unnecessary for reproduction;
- model/provider terms affecting redistribution;
- copyright, privacy and consent concerns;
- explicit data license for every published part.

Unknown rights default to **do not distribute**.

## 4. Credential and `.env` behavior

The accepted model is:

1. encrypted credential profiles are the default;
2. `.env` files can be imported into encrypted profiles;
3. ordinary project/config files store credential profile IDs, not secret values;
4. explicit secret-bearing `.env` export is supported with warnings and confirmation;
5. an expert may bind a profile to a persistent external `.env` file;
6. file-backed mode continuously reads only allowlisted variable names and displays plaintext-at-rest/cloud-backup warnings;
7. file-backed mode is never enabled silently;
8. the app never silently falls back from encrypted storage to plaintext persistence.

The UI provides reveal-folder, copy-variable-name, test-credential, rotate-profile and remove-profile actions without displaying the complete key by default.

Linux without a usable Secret Service remains an open design question. Until resolved, plaintext persistence is not an acceptable fallback.

## 5. System tray and long-running jobs

System-tray/background execution is required.

When the main window closes while any non-terminal job is active, the app MUST present:

- **Keep running in tray**;
- **Pause safely and quit**;
- **Cancel job and quit**.

Additional accepted defaults:

- launch at login is opt-in and disabled by default;
- native completion/error/quota notifications are enabled but configurable;
- sleep prevention is used only during critical submission/download/export stages where suspension could corrupt or lose work;
- ordinary inference between durable checkpoints should not permanently prevent sleep;
- tray state shows active job count and highest-severity state;
- OS shutdown/session-end attempts best-effort checkpointing without claiming guaranteed completion.

## 6. Atlas Document Studio

### 6.1 Editing model

The accepted design is hybrid:

- structured blocks/pages are the default and remain the portable, accessible foundation;
- controlled freeform page mode is included for advanced composition;
- freeform mode must still serialize into a versioned declarative schema;
- arbitrary HTML, JavaScript, executable plugins and unrestricted CSS are prohibited;
- freeform content must participate in pagination, print preflight, migration and missing-font handling.

### 6.2 Required templates

All original templates remain, plus two requested v1 templates:

1. Research Light;
2. Editorial Dark;
3. Gallery Minimal;
4. Technical Audit;
5. Executive Review;
6. **Traditional Chinese Academic**;
7. **16:9 Presentation Report**.

Traditional Chinese Academic MUST provide CJK-safe typography, scientific caption numbering, table/figure labels, conservative color use, headers/footers and an evidence appendix.

16:9 Presentation Report MUST produce landscape pages suitable for screen presentation while remaining a PDF document, not a PowerPoint substitute. It supports title, section, comparison, gallery, metric and appendix page patterns.

Fonts are included only when redistribution and embedding rights are verified. Otherwise the template declares installed-font requirements and deterministic fallbacks.

## 7. Detection model scope

The v1 strategy is representative tiers, not every upstream model.

### Required v1 models

- YOLOX-Tiny — low/resource baseline already used by this repository;
- YOLOX-S — medium tier;
- YOLOX-L — high tier;
- NanoDet-Plus-m-320 — low/resource baseline already used by this repository;
- NanoDet-Plus-m-416 — higher-resolution tier;
- NanoDet-Plus-m-1.5x-416 — higher-capacity tier.

### Deferred catalog candidates

- YOLOX-Nano;
- YOLOX-M;
- YOLOX-X;
- NanoDet-Plus-m-1.5x-320;
- unrelated model families until plugin/adapter governance is mature.

Every required model still needs an individual artifact manifest, real runtime smoke, decoding golden tests, resource metadata and rights review. `Required` means the adapter/catalog support is a v1 goal; it does not automatically authorize bundling the weight in the installer.

CPU ONNX Runtime remains the universal baseline. GPU/provider scope remains open for the next review round.

## 8. Open-source and distribution posture

The desktop app is fully open source.

### 8.1 App source

- App-specific source under `app/` is licensed Apache-2.0.
- Public source and public release binaries are required.
- Contributions to app code are accepted under the same project license unless a future contributor agreement explicitly changes this.
- Every release includes license, NOTICE/third-party notices and SBOM outputs.

Apache-2.0 is selected because it is permissive, provides an explicit patent license/termination structure, and is compatible with the MIT-licensed Electron/Vue/Vuetify framework code used as dependencies.

### 8.2 What the app license does not cover

The Apache-2.0 app license does not automatically relicense:

- pretrained model weights;
- COCO or other datasets;
- user media;
- generated sample corpus assets;
- premium Vuetify themes/templates;
- proprietary fonts/icons;
- provider names/logos;
- third-party binaries with their own licenses;
- content obtained from user-selected local files or URLs.

Each redistributed artifact must have its own provenance and license record.

### 8.3 Conservative anti-takedown policy

To reduce infringement and takedown risk:

- do not bundle model weights until explicit artifact-level redistribution approval exists;
- prefer official runtime download or user-supplied import when terms are unclear;
- do not copy premium Vuetify Store assets into the public repository; use only Vuetify's open-source framework and self-authored assets unless a redistribution license is documented;
- use open-licensed or self-authored icons, templates and fonts;
- maintain `THIRD_PARTY_NOTICES`, SBOM and source links;
- publish sample data only with rights/provenance manifest;
- include a documented correction/takedown contact and fast asset-withdrawal procedure;
- remove or replace a disputed optional asset without requiring the open-source app code to be deleted.

## 9. Acceptance impact

Round-two decisions add these mandatory acceptance gates:

- package smoke/update testing for all six artifact targets;
- both sample corpus tiers install, verify and open independently;
- no sample asset publishes without a complete license/provenance manifest;
- `.env` expert mode cannot activate without an explicit warning/confirmation;
- active jobs survive window close when tray execution is selected;
- the two new Atlas templates pass CJK/font/PDF visual regression tests;
- all six representative detector models have adapter, hash, smoke and license state coverage;
- app source distribution includes Apache-2.0 license, notices and SBOM;
- model/data assets with unknown rights are absent from installers and public sample Releases.

## 10. Remaining blocking questions

This round does not declare the specification implementation-ready. The next review should resolve at least:

1. packaging/updater stack (`electron-builder`/`electron-updater` versus alternatives);
2. Linux secret fallback without Secret Service;
3. packaged Python engine versus rewrite boundary;
4. v1 GPU acceleration scope;
5. default video/GIF representation in PDF;
6. imported-media copy/reference default;
7. generated-media enrollment into Atlas/Detection corpora.

See [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md).
