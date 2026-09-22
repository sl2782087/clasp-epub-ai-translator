# Changelog

All notable changes will be documented here. The project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.4.0] - 2026-09-22

### Added

- Hermes Agent compatibility metadata and direct nested-skill installation documentation.
- Interactive `configure --terminal` workflow for headless servers, with hidden API-key input, model discovery, connection testing, translation defaults, image-provider settings, and glossary import/editing.
- Hermes gateway guidance for per-book default/custom selection and verified EPUB document delivery.

### Changed

- Skill bundle now directly references every runtime script and operational reference so third-party Agent Skills installers include transitive support files.
- Documentation distinguishes the local desktop web page from the no-listener server terminal workflow.

## [0.3.0] - 2026-09-22

### Added

- Image-review context artifacts combining explicit and embedded glossaries, learned handoff renderings, book metadata, and bounded prose near each image.
- Explicit terminology precedence and conflict reporting.
- Pack-time enforcement that OCR-detected glossary terms are declared, reviewed, and rendered exactly in localized image text.
- Context checksum validation so edited or mismatched terminology cannot be packed silently.
- Bounded nearby prose context for the experimental automatic vision path.

### Changed

- Reviewed image decisions now record recognized text, translated text, matched terms, and terminology-review status.
- Image-context policy version now participates in resumable-work identity.

## [0.2.0] - 2026-09-22

### Changed

- Replaced the recommended one-call image path with a high-fidelity reviewed second stage inspired by the dedicated EPUB image-localization workflow.
- Image review now inventories every candidate including covers, generates contact sheets and a decision ledger, and selects editing methods by actual background and typography needs.
- The previous endpoint-driven `auto` and `all` paths remain available but are explicitly experimental.

### Added

- Surgical image repacking with real extension/MIME updates, resource-reference rewriting, XHTML text/spine preservation, and unchanged-image byte checks.
- Required `translate / keep / uncertain` decisions and delivery gates for text, visual, pixel, clean-background, and cover-typography review.
- Explicit edit-whitelist and protected-region pixel auditing.
- Lossless PNG optimization that accepts output only when decoded RGBA pixels remain identical.
- Regression tests for inventory, review gating, pixel constraints, optimization, and EPUB repacking.

## [0.1.0] - 2026-09-22

### Added

- Initial public Codex plugin and EPUB translation skill.
- Local configuration page with provider/model discovery, connection testing, defaults, plaintext credential storage, and manual terminology management.
- Chinese-only and bilingual output, Simplified/Traditional Chinese, layout choices, sample/full scope, resumable work, and optional Calibre checks.
- Optional image localization with provider selection, bounded candidate processing, caching, and local CJK text rendering.
- EPUB structure verification, visible-text contamination detection, atomic delivery, and versioned resume safety policies.
- Pinned temporary `bilingual_book_maker` fork containing the fix proposed in upstream PR #575.

[Unreleased]: https://github.com/sl2782087/clasp-epub-ai-translator/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/sl2782087/clasp-epub-ai-translator/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/sl2782087/clasp-epub-ai-translator/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/sl2782087/clasp-epub-ai-translator/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/sl2782087/clasp-epub-ai-translator/releases/tag/v0.1.0
