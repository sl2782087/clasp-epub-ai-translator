# Contributing

Thanks for improving Clasp EPUB AI Translator.

## Before opening a change

1. Search existing issues and pull requests.
2. Use only DRM-free, public-domain, self-authored, or synthetic fixtures. Never commit purchased books, API keys, provider responses containing private data, or generated translations you cannot redistribute.
3. Keep the wrapper provider-neutral and preserve the source EPUB.
4. Avoid hardcoded personal paths, account-specific model IDs, and platform-only assumptions.

## Development

Python 3.10+ and `uv` are recommended.

```bash
uv run --with 'Pillow>=10,<13' python -m unittest discover \
  -s plugins/clasp-epub-ai-translator/skills/clasp-epub-ai-translator/tests \
  -p 'test_*.py' -v
```

Run `git diff --check` and verify JSON manifests before submitting. New behavior should include focused tests, especially for ZIP paths, output validation, credential handling, resume identity, and cross-platform behavior.

## Pull requests

Explain the problem, the chosen behavior, security/privacy implications, tests run, and user-visible documentation changes. Keep unrelated refactors separate. By contributing, you agree that your contribution is licensed under the repository's MIT License.

All participants must follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
