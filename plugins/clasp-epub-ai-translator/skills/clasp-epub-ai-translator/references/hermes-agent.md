# Hermes Agent and headless servers

This skill is compatible with NousResearch Hermes Agent through the Agent Skills format. Hermes runs the same local wrapper as Codex; there is no relay service and no need to expose a configuration website.

## Install

On the server that runs Hermes Agent:

```bash
hermes skills install sl2782087/clasp-epub-ai-translator/plugins/clasp-epub-ai-translator/skills/clasp-epub-ai-translator
```

Check for and install future skill updates with:

```bash
hermes skills check
hermes skills update
```

The server needs Python 3.10 or newer and [`uv`](https://docs.astral.sh/uv/). Calibre is optional. If it is not installed, set the Calibre default to `none`. Reviewed image localization also needs a CJK font and a vision-capable agent or manual visual review; prose translation works without image tooling.

After installation, invoke the skill in Hermes with `/clasp-epub-ai-translator` or ask Hermes to use that skill for an EPUB. Upload the source EPUB through the active Hermes gateway or place it in a filesystem location readable by Hermes.

## Configure safely in the terminal

Open a real interactive shell or provider console on the Hermes server, change to the installed skill directory, and run:

```bash
uv run --script scripts/bootstrap.py check
uv run --script scripts/bootstrap.py install
uv run --script scripts/epub_translate.py configure --terminal
```

The terminal wizard can select providers and defaults, fetch model lists, test endpoints, edit/import the reusable glossary, and configure experimental image models. It uses hidden input for API keys. A blank key keeps the environment variable or previously saved value. It intentionally has no `--api-key` option, does not print keys, and requires an interactive TTY.

Do not paste API keys into a Hermes chat, Telegram/Discord message, command argument, shell history, or skill file. The wrapper stores newly entered keys as plaintext secret material with user-only file permissions where supported.

Default Linux paths are:

```text
~/.config/clasp-epub-ai-translator/settings.json
~/.config/clasp-epub-ai-translator/credentials.json
~/.config/clasp-epub-ai-translator/glossary.txt
```

For a service account, these paths are under that account's home directory. Set `EPUB_TRANSLATOR_CONFIG`, `EPUB_TRANSLATOR_CREDENTIALS`, and `EPUB_TRANSLATOR_GLOSSARY` to explicit private paths when the Hermes service has a nonstandard or read-only home. Give the service user read/write access to those files and the book/output directories. Do not put the credential file in the Git repository or a shared upload directory.

Existing provider environment variables take precedence over `credentials.json`. This is useful with a service manager's secret/environment configuration, but the terminal file workflow is portable and does not require it.

## Per-book behavior

Before every book, Hermes must ask whether to use all saved defaults or customize only that run. Saved defaults use `--provider default`; a one-off provider selection uses `--provider custom --engine ...` and does not rewrite settings. Always inspect first, show the exact plan, and wait for confirmation before `run --yes` consumes model quota.

Use `openai`, `gemini`, `claude`, `qwen`, `deepl`, `ollama`, or `google` on a server unless that same server actually has an authenticated Codex CLI. An OpenAI-compatible self-hosted endpoint uses engine `openai` with its explicit API Base and model name. `ollama` defaults to `http://localhost:11434/v1`; if Ollama is on another host, enter its reachable server URL.

## Gateway input and delivery

Gateway uploads may be copied into a Hermes workspace. Resolve and inspect the actual local `.epub` path; never infer a path from an untrusted filename. The skill refuses DRM-protected input and never overwrites the source.

After verification succeeds, return the final absolute EPUB path on its own line followed by:

```text
[[as_document]]
```

This lets supported Hermes gateways deliver the file as an attachment. If the gateway cannot attach it, report the absolute path and keep the verified file on the server for authorized retrieval. Never attach `credentials.json`, work caches, or source books unless the user explicitly requests and is authorized to receive them.
