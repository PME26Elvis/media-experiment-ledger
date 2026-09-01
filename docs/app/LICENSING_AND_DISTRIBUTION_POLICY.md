# Licensing and Distribution Policy

> Applies to: Media Experiment Ledger Studio (`app-main`)  
> Policy status: **accepted baseline**  
> This document is a project policy, not legal advice.

## 1. Goals

The project is fully open source, but open-source app code does not imply that every model weight, generated image, provider response, font, icon, dataset or binary can be redistributed under the same license.

The policy has two simultaneous goals:

1. keep the complete desktop application source and public binaries openly available;
2. reduce copyright, trademark, data-license and model-weight redistribution risk enough that an optional disputed asset can be removed without threatening the repository itself.

## 2. Application source license

App-specific source under `app/` is licensed under the **Apache License 2.0**.

Rationale:

- permissive use, modification and redistribution;
- explicit patent grant and patent-termination terms;
- clear NOTICE mechanism;
- compatible use with MIT-licensed Electron, Vue and Vuetify dependencies;
- appropriate for public binaries and contributions;
- does not force unrelated user projects or generated reports to adopt the app's license.

The license applies only to files for which this repository has authority to license. Files that contain their own license headers or live in a separately licensed data/model package retain those terms.

## 3. Public distribution posture

The project requires:

- public source code;
- public reproducible build instructions;
- public Windows, macOS and Linux binaries when release acceptance passes;
- checksums;
- SBOM;
- third-party notices;
- source links and version identities for shipped dependencies;
- a security and rights-reporting contact/process;
- no paywall requirement for ordinary app functionality.

The app may call paid third-party APIs with user-supplied credentials, but API fees and provider terms are external to the app license.

## 4. License layers

The release pipeline treats these as separate layers.

### 4.1 App source

License: Apache-2.0.

Includes:

- Electron main/preload/renderer code authored for this product;
- local engine adapters authored by this project;
- project schemas and migrations;
- self-authored templates, icons and documentation where no separate license is stated;
- build and release automation.

### 4.2 Third-party source dependencies

Each dependency must be represented in the lockfile, SBOM and notices. The project MUST:

- identify package name/version/license;
- retain required copyright/license text;
- flag unknown, custom, source-available or strong-copyleft dependencies for explicit review;
- avoid packages whose terms conflict with public binary redistribution;
- prevent dev-only packages from being silently shipped in production archives;
- scan both JavaScript and packaged Python/native dependency trees.

Permissive dependencies such as MIT, BSD and Apache-2.0 are not automatically risk-free; notices and binary obligations still apply.

### 4.3 Model adapters

Adapters/decoders authored by the project may be Apache-2.0.

An adapter does not grant rights to a model weight. The registry records adapter and artifact licensing separately.

### 4.4 Pretrained model weights

Every model artifact has one of these states:

- `verified-bundle`: explicit redistribution permission verified; installer bundling allowed;
- `verified-download`: official/approved runtime download allowed but installer bundling not selected;
- `user-supplied-only`: app may operate on a user-selected file through an allowlisted adapter;
- `needs-review`: visible only in planning/developer diagnostics;
- `blocked`: known rights, integrity or compatibility problem.

Required evidence before `verified-bundle`:

- exact source URL/release/tag;
- exact filename, size and SHA-256;
- artifact-specific license or documented upstream clarification;
- training-dataset attribution/usage notes where relevant;
- conversion/export provenance for ONNX artifacts;
- required notices;
- review date and reviewer;
- revalidation trigger when upstream terms or artifact identity changes.

Repository source code being Apache-2.0 is not by itself sufficient proof that every linked pretrained weight may be repackaged in an installer.

### 4.5 Datasets and labels

COCO labels, evaluation data and other datasets retain their own provenance and terms. A labels JSON file is shipped only when its origin and allowed redistribution are recorded.

The app MUST NOT imply that COCO-pretrained inference outputs are validated accuracy results on generated media without ground-truth annotations.

### 4.6 Sample corpus

Every Quick Start or Full Research corpus Release includes a data manifest that records:

- publisher/curator;
- source generation/import process;
- provider/model names;
- whether prompts are included;
- sanitization actions;
- copyright/license assertion;
- privacy review;
- excluded files/reasons;
- asset hashes;
- permitted use and attribution;
- takedown/correction process.

Target public license is **CC BY 4.0** only where the maintainer has verified enough rights to grant that license. When rights are unclear, the file is withheld or published under a specific narrower notice only after review. Unknown rights default to no redistribution.

The code license never automatically covers corpus ZIPs.

### 4.7 Fonts

Fonts must be classified as:

- allowed to bundle and embed in generated PDFs;
- allowed to bundle but not embed;
- system-only dependency;
- user-supplied;
- blocked/unknown.

Each Atlas template declares its font requirements and deterministic fallback chain. PDF preflight warns when an expected font cannot be embedded.

### 4.8 Icons, illustrations and UI assets

Allowed sources:

- self-authored assets;
- open-source icon sets with retained notices;
- public-domain/CC0 assets with recorded source;
- separately licensed assets whose license explicitly permits source and binary redistribution.

Prohibited by default:

- copied premium themes/templates;
- stock assets without redistribution rights;
- third-party product logos used as app branding;
- scraped website images;
- assets whose source cannot be reconstructed.

Vuetify's open-source framework may be used according to its framework license. Premium Vuetify Store products are separate commercial assets and MUST NOT be committed or redistributed unless the exact purchased license permits that use.

### 4.9 Provider names and trademarks

Provider/model names may be used descriptively to identify compatibility. The app must:

- avoid implying endorsement;
- avoid using third-party logos in the main brand without permission;
- display “unofficial integration” where confusion is plausible;
- link to official terms/source in detail views;
- allow a provider integration to be disabled/renamed if a legitimate trademark complaint arises.

## 5. Required repository files

Before implementation-ready status:

```text
app/LICENSE
app/NOTICE
app/THIRD_PARTY_NOTICES.md          # generated and reviewed before release
app/DEPENDENCY_LICENSE_POLICY.md    # allow/review/block rules
app/model-registry/*.json           # artifact-level rights/status
app/data-licenses/*.json            # sample corpus manifests
```

Generated Release outputs:

```text
Media-Experiment-Ledger-Studio-<version>-SBOM.spdx.json
Media-Experiment-Ledger-Studio-<version>-THIRD-PARTY-NOTICES.txt
Media-Experiment-Ledger-Studio-<version>-SHA256SUMS.txt
Media-Experiment-Ledger-Studio-<version>-release-manifest.json
```

## 6. Dependency intake gate

A production dependency cannot be added only because it solves a technical problem. Intake records:

- package/source;
- version pin/range;
- maintainer activity and security posture;
- license and notices;
- transitive dependency impact;
- whether code is shipped or build-only;
- binary/native components;
- platform support;
- replacement/removal plan;
- approval status.

CI fails on:

- missing/unknown production license;
- dependency not present in SBOM;
- forbidden license policy match;
- unapproved native binary;
- notice-generation mismatch;
- model/data asset without a rights manifest.

## 7. Release gates

A public app release cannot become final unless:

- app license is present in every installer/archive;
- notices and SBOM match packaged contents;
- checksums match uploaded assets;
- signing identity is verified where required;
- every bundled model/data/font has an approved manifest;
- no credential or private path appears in assets;
- sample corpus tags/hashes referenced by the app release exist and are final;
- automated install/update tests pass;
- a human reviews Release Notes and rights exceptions.

## 8. Takedown and correction resilience

The project should be structured so an optional asset can be withdrawn without deleting the app repository.

Required process:

1. record the complaint and exact asset/version;
2. temporarily disable new downloads when credible review is needed;
3. preserve private audit evidence without republishing disputed bytes;
4. remove the asset from current manifests/releases where legally and technically appropriate;
5. publish a corrected manifest/version;
6. notify affected users in Model/Data Manager;
7. replace with official runtime download, user-supplied mode or a clean alternative;
8. document resolution without making unsupported legal claims.

Immutable historical GitHub Releases are not treated as a reason to knowingly keep distributing disputed optional assets; release repair/removal policy must follow GitHub capabilities and documented evidence.

## 9. Contributions

By contributing app code, contributors agree that their contribution is licensed under Apache-2.0 unless the file clearly states another accepted license.

Contributors must not submit:

- proprietary employer/client code without authorization;
- copied premium UI templates;
- model weights as ordinary source attachments;
- datasets/media without rights metadata;
- credentials or private provider responses;
- third-party code with removed notices.

A Developer Certificate of Origin sign-off MAY be added before broad external contribution begins. A CLA is not initially required.

## 10. Current model policy

For YOLOX and NanoDet-Plus:

- their upstream code repositories identify Apache-2.0 for source code;
- baseline and representative model adapters remain planned;
- model weights default to download-on-demand or user-supplied until each exact artifact passes review;
- official source links, size and SHA-256 are shown before download;
- installer bundling is prohibited by default;
- changing a model URL/hash triggers a new rights/integrity review.

## 11. Acceptance criteria

- app source includes Apache-2.0 license;
- public binaries include license/notices/SBOM;
- no premium or proprietary UI asset appears in the public tree without explicit redistribution rights;
- every model/data/font artifact has an independent manifest and status;
- unknown rights are blocked from release;
- automated CI checks enforce dependency/model/data license policy;
- Model Manager and Sample Data Manager expose source, hash, license state and notices;
- correction/takedown flow can disable an optional asset without breaking project files that already reference its immutable identity.
