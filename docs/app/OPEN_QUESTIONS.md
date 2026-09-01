# Desktop Product Decision Register

Status: **no blocking product questions remain**  
Specification baseline: `2026-07-22.3`

The controlling decision is:

> Mature capabilities are completed in v1 when their main cost is engineering volume, cross-platform integration or testing effort. They are not deferred merely to create a smaller MVP.

The product specification is `implementation_ready`. Implementation remains `not_started` until the user explicitly requests it.

All questions from specification rounds 1–3 are resolved in:

- `SPECIFICATION_ROUND_02.md`;
- `SPECIFICATION_ROUND_03.md`;
- `DECISIONS.md`;
- `app-product-contract.json`.

Resolved areas include product identity, all six packages, sample corpora, encrypted credentials and portable vault, tray/background jobs, Atlas editor/templates/PDF behavior, model acquisition, detector variants, Apache-2.0 distribution, electron-builder/electron-updater, packaged Python engine, signing/notarization, DirectML/CUDA/CoreML, adaptive import, Generated Media enrollment, Pinia/TanStack Query, sanitized prompts, five locales, custom templates, user ONNX adapters, GitHub publishing, OS schedulers, cloud-folder sync, telemetry and reference hardware.

There are no unresolved P0/P1/P2 product decisions required before implementation.

During implementation, evidence may uncover a platform limitation, dependency regression, rights problem, security issue or measurable performance contradiction. Such discoveries require an ADR/spec correction and user-visible explanation. They MUST NOT silently remove or defer a required v1 capability.

## Next authorized action

Wait for the user to explicitly request implementation. At that point development follows:

- `SPECIFICATION_ROUND_03.md`;
- `V1_TDD_SDD_ENGINEERING_POLICY.md`;
- `V1_SCOPE_ACCEPTANCE_MATRIX.md`;
- `app-product-contract.json` version `2026-07-22.3`.