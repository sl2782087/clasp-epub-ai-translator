# Clasp EPUB AI Translator

**暗扣 AI 电子书翻译** is an open-source Codex plugin and skill for translating DRM-free EPUB books into Chinese-only or Japanese–Chinese bilingual editions. It keeps the source book untouched, preserves EPUB structure, supports configurable model providers and terminology, and can optionally localize text-bearing images.

[简体中文说明](README.zh-CN.md) · [Disclaimer](DISCLAIMER.md) · [Privacy](PRIVACY.md) · [Security](SECURITY.md)

> [!IMPORTANT]
> This project does not remove or bypass DRM. You are responsible for ensuring that you have the right to process, translate, and share each book and image.

## Highlights

- Guided choices for Chinese-only/bilingual output, Simplified/Traditional Chinese, horizontal/vertical/preserved layout, translation style, context, sample/full scope, and optional Calibre checks.
- A local-only configuration page for providers, API endpoints, model discovery, connection tests, defaults, and a reusable manual glossary.
- Plaintext credentials stored separately from ordinary settings with restrictive file permissions where supported. Saved keys are never returned to the browser.
- Optional image localization using a vision model, an image-edit model, and local CJK text rendering.
- Structure validation plus a visible-text contamination gate that blocks model analysis, self-checks, and JSON/schema residue from being silently delivered.
- Atomic final delivery: the source EPUB is never overwritten, and the visible output appears only after validation succeeds.
- Resume identity includes the prompt, contamination detector, retry policy, source, and glossary fingerprints.

## Requirements

- Codex with plugin support
- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/)
- Network access and credentials for the model provider you choose, unless using a local provider
- A CJK font for image localization; set `CLASP_EPUB_FONT` if automatic discovery fails
- Calibre is optional

macOS, Linux, and Windows are supported by the wrapper. Provider and upstream translator behavior may vary by platform.

## Install

Add this repository as a Git-backed marketplace, then install the plugin:

```bash
codex plugin marketplace add sl2782087/clasp-epub-ai-translator
codex plugin add clasp-epub-ai-translator@clasp-epub-ai-translator
```

Start a new Codex task after installation so the skill is loaded. You can then ask:

```text
Use $clasp-epub-ai-translator to inspect this EPUB and recommend translation settings.
```

For development or manual use, clone the repository and work in:

```text
plugins/clasp-epub-ai-translator/skills/clasp-epub-ai-translator
```

Check the local environment, then explicitly install the pinned translator dependency if needed:

```bash
uv run --script scripts/bootstrap.py check
uv run --script scripts/bootstrap.py install
```

The install command currently pins [`sl2782087/bilingual_book_maker@4e4e20c`](https://github.com/sl2782087/bilingual_book_maker/commit/4e4e20cead3431e4880b505795a19adf1537ca1a). That fork contains the translation-output contamination fix submitted upstream as [bilingual_book_maker#575](https://github.com/yihong0618/bilingual_book_maker/pull/575). The dependency will return to an upstream release after the fix is merged and published.

## Workflow

The skill normally drives these commands for you:

```bash
# Read metadata and structure without model calls
uv run --script scripts/epub_translate.py inspect /path/to/book.epub

# Open a temporary configuration page bound to 127.0.0.1
uv run --script scripts/epub_translate.py configure

# Show an exact, non-mutating plan
uv run --script scripts/epub_translate.py plan /path/to/book.epub

# Run only after reviewing the plan
uv run --script scripts/epub_translate.py run /path/to/book.epub --yes

# Independently verify an EPUB
uv run --script scripts/epub_translate.py verify /path/to/output.epub
```

Use `--help` for the complete interface. A two-chapter sample is the default; review it before paying for a full novel.

## Configuration and data flow

The configuration page is book-independent and uses no external web assets. By default, settings live under the platform configuration directory named `clasp-epub-ai-translator`. Provider keys are stored in a separate plaintext `credentials.json`, and the reusable terminology file is `glossary.txt`. Environment variables can override all three paths.

Book text and, when enabled, images are sent to the provider selected by the user. The project does not operate a relay server or receive this content. Local providers can keep processing local, subject to their own configuration. See [PRIVACY.md](PRIVACY.md) for exact behavior.

## Safety model

Model output is untrusted. The pinned translator rejects high-confidence analysis/self-check residue before it enters context or resumable state, retries only the affected paragraph, and stops with the EPUB member and anchor after repeated failure. The wrapper independently scans visible spine text before publication. It does not use a naive “any English is bad” rule, and it treats Japanese quotation marks spanning paragraphs as valid.

These checks reduce risk; they do not prove translation accuracy. Always review important passages and sample output.

## Development

```bash
uv run --with 'Pillow>=10,<13' python -m unittest discover \
  -s plugins/clasp-epub-ai-translator/skills/clasp-epub-ai-translator/tests \
  -p 'test_*.py' -v
```

See [CONTRIBUTING.md](CONTRIBUTING.md). Please report vulnerabilities privately as described in [SECURITY.md](SECURITY.md), and never attach copyrighted books or API keys to an issue.

## License

Project code and documentation are available under the [MIT License](LICENSE). External tools and services keep their own licenses and terms; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Disclaimer

This software is provided “as is,” without warranties. AI output may be inaccurate, unsafe, incomplete, or costly. Use only content you are authorized to process. Full terms are in [DISCLAIMER.md](DISCLAIMER.md).
