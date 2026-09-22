# 暗扣 AI 电子书翻译

**暗扣 AI 电子书翻译（Clasp EPUB AI Translator）** 是一个开源的 Codex 插件与 Skill，用于把无 DRM 的 EPUB 翻译成纯中文或日中双语版本。它不会覆盖原书，尽量保留 EPUB 的封面、导航、图片、ruby、内部链接与排版结构，并支持模型接口、术语表、图片本地化和交付前安全检查。

[English](README.md) · [免责声明](DISCLAIMER.md) · [隐私说明](PRIVACY.md) · [安全政策](SECURITY.md)

> [!IMPORTANT]
> 本项目不移除、不破解也不绕过 DRM。你有责任确认自己有权处理、翻译和传播相关书籍及图片。

## 主要功能

- 可选择纯中文/双语、简体/繁体、横排/竖排/保持原样、翻译风格、上下文方式、样章/全书以及 Calibre 后处理。
- 本地可视化配置页：配置模型、API Base、Key、默认翻译选项，拉取模型列表并测试接口。
- 支持可复用的手工术语表；普通配置、明文凭据与术语文件相互分离。
- 可选图片翻译：视觉模型识别与翻译、图片模型去字补背景，再用本地中文字体回写。
- 模型输出污染防护：在译文进入上下文/缓存前识别分析、自检和 JSON 残片，并在交付前再次扫描 EPUB 正文。
- 原子交付：结构和正文检查都通过后才产生最终可见文件，永不覆盖源 EPUB。

## 环境要求

- 支持插件的 Codex
- Python 3.10 或更高版本
- [`uv`](https://docs.astral.sh/uv/)
- 所选模型服务的网络与凭据；使用本地服务时除外
- 图片翻译需要中文字体；自动发现失败时设置 `CLASP_EPUB_FONT`
- Calibre 可选

包装器支持 macOS、Linux 和 Windows；不同模型服务及上游翻译工具的实际兼容性可能有差异。

## 安装

把本仓库添加为 Git marketplace，然后安装插件：

```bash
codex plugin marketplace add sl2782087/clasp-epub-ai-translator
codex plugin add clasp-epub-ai-translator@clasp-epub-ai-translator
```

安装后请新建一个 Codex 任务，让新 Skill 被加载。调用示例：

```text
使用 $clasp-epub-ai-translator 检查这个 EPUB，并推荐翻译配置。
```

开发或手工运行时，进入以下目录：

```text
plugins/clasp-epub-ai-translator/skills/clasp-epub-ai-translator
```

先检查环境；确实缺少翻译器时再执行安装：

```bash
uv run --script scripts/bootstrap.py check
uv run --script scripts/bootstrap.py install
```

目前安装脚本固定使用 [`sl2782087/bilingual_book_maker@4e4e20c`](https://github.com/sl2782087/bilingual_book_maker/commit/4e4e20cead3431e4880b505795a19adf1537ca1a)。这个 fork 包含译文混入模型分析内容的安全修复，已通过 [bilingual_book_maker#575](https://github.com/yihong0618/bilingual_book_maker/pull/575) 提交上游。上游合并并发布后，项目会切回正式上游版本。

## 使用流程

Skill 通常会代你完成以下流程：

```bash
# 只读取元数据与结构，不调用模型
uv run --script scripts/epub_translate.py inspect /path/to/book.epub

# 在 127.0.0.1 打开临时配置页
uv run --script scripts/epub_translate.py configure

# 生成不修改文件、不调用模型的明确计划
uv run --script scripts/epub_translate.py plan /path/to/book.epub

# 审核计划后才执行
uv run --script scripts/epub_translate.py run /path/to/book.epub --yes

# 独立验证 EPUB
uv run --script scripts/epub_translate.py verify /path/to/output.epub
```

完整参数以 `--help` 为准。默认先翻译两章样章，建议确认质量与费用后再处理全书。

## 配置、Key 与数据流

配置页不绑定任何书籍，也不加载外部网页资源。默认配置保存在系统用户配置目录下的 `clasp-epub-ai-translator` 文件夹中；Key 单独写入明文 `credentials.json`，术语表写入 `glossary.txt`。支持环境变量覆盖路径。程序会在操作系统支持时把凭据文件权限限制为仅当前用户，但它仍然是明文文件，请谨慎备份或同步。

书籍正文会发送给你选择的模型服务；启用图片翻译时，选中的图片也会发送。项目本身没有中转服务器，也不会接收这些内容。使用本地模型能否完全离线取决于你的服务配置。详情见 [PRIVACY.md](PRIVACY.md)。

## 安全边界

模型输出始终被视为不可信数据。固定版本的翻译器会在输出进入上下文或恢复缓存之前检测高置信度的分析、自检与 schema/JSON 残留，只重试污染条目；连续失败则报告 XHTML 成员和锚点并停止。包装器在最终交付前还会独立扫描 spine 正文。它不会因为单个英文词就误判，也不会要求日文引号在每个段落内自行闭合。

这些措施只能降低风险，不能保证译文准确。重要作品仍应人工抽查或校对。

## 参与开发

```bash
uv run --with 'Pillow>=10,<13' python -m unittest discover \
  -s plugins/clasp-epub-ai-translator/skills/clasp-epub-ai-translator/tests \
  -p 'test_*.py' -v
```

请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。安全问题请按 [SECURITY.md](SECURITY.md) 私下报告；不要在 Issue 中上传受版权保护的电子书或 API Key。

## 许可与免责声明

本项目代码和文档采用 [MIT License](LICENSE)。外部工具与服务适用各自的许可证和条款，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。软件按“原样”提供，AI 译文可能错误、不完整、不安全或产生费用；完整说明见 [DISCLAIMER.md](DISCLAIMER.md)。
