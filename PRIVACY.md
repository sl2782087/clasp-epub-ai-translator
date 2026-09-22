# Privacy / 隐私说明

## What the project stores locally

- `settings.json`: non-secret provider and translation defaults.
- `credentials.json`: plaintext provider keys, stored separately with user-only permissions where the operating system supports them.
- `glossary.txt`: reusable terminology chosen by the user.
- Hidden work directories: source copies, prompts, checkpoints, caches, validation reports, intermediate EPUBs, and image context files containing terminology, handoff notes, metadata, and bounded nearby prose needed for resume and audit.
- Final EPUB/AZW3 output in the user-selected output directory.

The source EPUB is never overwritten. The local configuration page binds to `127.0.0.1`, loads no external assets, does not receive an EPUB, and never returns a previously saved key to the browser.

## What leaves the device

Text selected for translation is sent directly to the provider configured by the user. High-fidelity reviewed image localization uses local deterministic tools by default; images, masks, or selected terminology/nearby prose leave the device only when the user authorizes a remote vision or generative-editing step. The explicitly experimental automatic image modes send candidate images, the configured glossary (bounded to 30 KB), and visible prose near that candidate (bounded to 8 KB) to their configured endpoints. They do not automatically send the whole book as image context. Model discovery and connection tests send endpoint and authentication requests but no book text. The project has no hosted relay, analytics, telemetry, advertising, or developer-operated data collection.

Provider handling is governed by that provider's terms and privacy settings. A local endpoint may keep content local, but this project cannot verify the endpoint's implementation.

## User controls

- Choose a local or remote provider and API endpoint.
- Keep image translation disabled.
- Override settings, credentials, and glossary paths with documented environment variables.
- Delete local configuration and work/output directories when no longer needed.
- Inspect the exact plan before model calls begin.

Do not commit, upload, or share `credentials.json`, books, caches, or translated output unless you are authorized to do so.

## 中文摘要

项目只在本地保存普通设置、明文凭据、术语表、中间工作文件、图片上下文文件和输出文件。图片上下文可能含书籍元数据、术语、翻译交接摘要及每张图附近的有限正文。配置页仅监听 `127.0.0.1`，不加载外部资源，不接收书籍，也不会把已保存的 Key 回显到浏览器。

正文会直接发送到用户选择的模型服务。高保真图片流程默认使用本地确定性工具；只有用户明确同意远程视觉或生成式编辑步骤时，对应图片、蒙版及选中的有限术语/邻近正文才会发送。明确标为实验性的自动图片模式会向配置接口发送候选图片、最多 30 KB 的已配置术语表和最多 8 KB 的图片附近正文，不会自动把整本书作为图片上下文发送。模型列表与接口测试会访问服务商，但不发送书籍正文。项目没有中转服务器、统计、遥测、广告或开发者侧数据收集。服务商如何处理数据，以其条款和隐私设置为准。

请勿提交或分享 `credentials.json`、电子书、缓存或翻译结果，除非你已获得相应授权。
