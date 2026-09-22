# Translation options

Use the wrapper's `--help` as the exact interface. This reference explains selection policy.

## User-facing choices

Run `configure` for the book-independent defaults page. It saves model/API settings and translation defaults in the platform user-config directory. On macOS this is `~/Library/Application Support/clasp-epub-ai-translator/settings.json`; Linux uses `${XDG_CONFIG_HOME:-~/.config}/clasp-epub-ai-translator/settings.json`; Windows uses `%APPDATA%\\clasp-epub-ai-translator\\settings.json` when available. `EPUB_TRANSLATOR_CONFIG` can override the settings path. Existing installations automatically read the legacy `epub-ai-translator` directory when the new settings file does not exist.

API keys entered there are stored per provider in a separate `credentials.json` beside `settings.json`, or at `EPUB_TRANSLATOR_CREDENTIALS` when overridden. The wrapper creates it with user-only permissions where supported, never returns saved keys to the browser, and injects a selected key only into the translator child process. This is a plaintext portability file: protect it when copying, backing up, or syncing it. Existing provider environment variables take precedence over this file.

At translation time choose one model source:

- `--provider default`: use the saved default model configuration, falling back to Codex when no file exists.
- `--provider custom --engine ... [--model ...] [--api-base ...]`: use a one-off selection without changing the saved default.

The values below are saved as defaults by the page. Explicit command-line options override them for one run without changing the saved file. Books, output directories, and custom glossary paths are never bound to the defaults page; the page manages its own reusable `glossary.txt`.

| Choice | Values | Default |
|---|---|---|
| Output | `chinese`, `bilingual` | `chinese` |
| Chinese script | `zh-hans`, `zh-hant` | `zh-hans` |
| Layout | `horizontal`, `vertical`, `preserve` | `horizontal` |
| Quality | `economy`, `balanced`, `quality` | `balanced` |
| Style | `faithful`, `literal`, `polished` | `faithful` |
| Context | `session`, `window`, `none` | `session` |
| Scope | `sample`, `full` | `sample` |
| Saved manual glossary | `on`, `off` | `off` |
| Image translation | `off`, `review`, `auto`, `all` | `off` |
| Image provider | `reuse`, `custom` | `reuse` |
| Vision model | provider model id | empty; select from provider |
| Image-edit model | provider model id | empty; select from provider |
| Image quality | `low`, `medium`, `high` | `low` |
| Image candidate limit | `0` to `100` (`0` = unlimited) | `2` |
| Include cover | `on`, `off` | `off` |
| Calibre | `metadata`, `azw3`, `none` | `metadata` |

`sample` selects the first distinct chapter documents from EPUB navigation, falling back to text-bearing spine items. `--sample-chapters` defaults to 2.

## Engines

- `codex`: uses the existing Codex CLI login and stores no key. Leave the model empty to use the CLI default, or enter a model available to your account.
- `openai`: uses `OPENAI_API_KEY`. Fetch the models exposed by the configured endpoint or enter one explicitly.
- `gemini`, `claude`, `qwen`, and `deepl`: use their conventional environment variables. Prefer an explicit `--model` when model choice matters.
- `google`: free machine translation, with weaker literary context and no style prompt.
- `ollama`: requires `--model`; defaults to `http://localhost:11434/v1` and keeps text local to that server.

The visual page shows whether the selected engine already has credentials. “获取模型列表” replaces the free-text model field with a full dropdown populated from provider-native endpoints; the dropdown includes an option to return to manual entry. “测试接口” checks the address and authentication without model generation. A key currently typed into the form is used only for that request; otherwise the environment or saved credential is used. The page never displays a saved key, asks for a book, or creates a translation plan.

The image section has its own model-list and connection-test controls. `reuse` uses the current `openai`, `qwen`, or `ollama` OpenAI-compatible endpoint and key. `custom` uses the separate image API Base and the `image_openai` entry in `credentials.json`; `EPUB_TRANSLATOR_IMAGE_API_KEY` takes precedence. A separately typed image key is used only for that request until the form is saved. The connection test lists models only and does not invoke vision or image generation.

OpenAI-compatible providers, Qwen, Gemini, Claude, and Ollama expose model-list endpoints. Codex uses the CLI default or a manually entered model, Google free translation has a fixed engine, and DeepL has no model list; DeepL connection testing uses its read-only usage endpoint. Tests have a short timeout, bounded JSON responses, and refuse credential-carrying redirects. A provider may still count a list or usage request against rate limits even though no generation occurs.

For a novel, prefer `balanced` first. Use `quality` after comparing the same sample. Economy mode is suitable for a rough draft.

## Layout

- `preserve` keeps the source writing direction.
- `horizontal` changes vertical XHTML roots to horizontal and changes OPF page progression to left-to-right. It does not convert the EPUB through Calibre.
- `vertical` changes text-bearing horizontal documents to vertical right-to-left while leaving covers and image-only pages alone.

All three modes repackage the EPUB with POSIX path normalization before validation. This repairs safe parent-directory references emitted literally by some `bbook_maker`/EbookLib combinations, while refusing paths that would escape the EPUB root or collide after normalization.

## Glossaries and style

The configuration page edits a reusable UTF-8 `glossary.txt` beside `settings.json`; `EPUB_TRANSLATOR_GLOSSARY` can override its location. Each non-comment line is `source -> translation` or `source → translation`; blank lines, full-line comments, and trailing `# notes` are supported. Enabling it in defaults applies it automatically. Use `--default-glossary off` to skip it for one run, or pass `--glossary /absolute/path/terms.txt` to use a different file for that run. A custom path takes precedence over the saved glossary. Keep `--glossary-auto off` unless the chosen model reliably reports its own renderings.

`faithful` preserves clues, ambiguity, register, names, punctuation, and paragraph structure. `literal` minimizes stylistic smoothing. `polished` produces more idiomatic literary Chinese without adding or omitting facts.

## Translation content safety

Japanese dialogue may open with `「` in one paragraph and close with `」` in a later paragraph. This is valid source structure; neither prompting nor validation requires each paragraph to balance quotation marks independently.

The installed translator validates every returned translation before adding it to session context or resumable state. High-confidence model-process residue uses combined signals, such as a JSON tail followed by `Wait source last ...`, explicit source-punctuation self-check language, or model-work statements about the translation field. A single English word, ordinary English dialogue, JSON example, code fence, or label such as a book title does not by itself fail. When one batch item fails, only that item is retried: once with a strict translation-only correction and once as a single paragraph with adjacent read-only context. A second failure stops the run and identifies the XHTML member and anchor.

The wrapper then performs an independent delivery scan over visible text in OPF spine XHTML/HTML, excluding `head`, `script`, `style`, and non-spine resources. High-confidence findings prevent the final EPUB from being published; medium-confidence findings remain warnings in the report. The hidden work directory receives `content-validation-report.json`. The visible destination is created by atomic rename only after ZIP/XML/package validation and this content gate both pass.

Prompt, detector, and retry-policy versions are part of the work-directory configuration hash and the translator checkpoint fingerprint. Updating these policies therefore invalidates older resumable output instead of silently inheriting it.

## Image localization

Use `--image-translation review` for deliverable quality. The prose wrapper produces a clearly named text-only intermediate, then creates `image-review/inventory.json`, `decisions.json`, `image-context.json`, `image-context.md`, extracted originals, and contact sheets. The context merges the active manual glossary, the translated EPUB's embedded glossary, stable handoff renderings, metadata, and bounded nearby prose. Explicit glossary entries win; conflicts are reported. The reviewed pass includes the cover, does not skip images solely by size, and requires a recorded decision for every candidate plus OCR/translation/matched-term fields for each translated image. Follow [image-workflow.md](image-workflow.md) to choose deterministic local edits, bounded repair, full-title cover typesetting, or SVG text editing; run terminology, semantic, visual, and pixel checks separately before packing.

`auto` and `all` retain the older one-call convenience pipeline for compatibility. They use normalized model boxes, an OpenAI-compatible image-edit endpoint, local text rendering, and a simple pixel mask. The vision request receives the configured glossary and bounded visible prose near that image, not the whole book. These modes may be useful for disposable previews, but they cannot inspect clean plates, typography groups, text correctness, or every visual seam and are therefore experimental. `image_provider`, vision/edit models, quality, limit, and cover options apply only to those experimental modes.

Reviewed replacements are packed with real file extensions and matching OPF MIME types; affected XHTML/CSS references are rewritten while visible XHTML text, spine order, and untouched image bytes are verified unchanged. Run the normal structure/content verifier again after packing.

## Calibre

Calibre is discovered on `PATH`, in the standard macOS application bundle, or in the usual Windows installation directories.

- `metadata` runs `ebook-meta` as a read-only final check.
- `azw3` creates a separate AZW3 after the EPUB passes validation.
- `none` skips Calibre.

Do not add a book to the Calibre library or launch `ebook-viewer` unless the user asks after seeing the output path.
