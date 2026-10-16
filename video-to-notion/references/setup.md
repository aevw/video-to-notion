# 首次配置与检查

Agent 先检测，只准备本次缺少的部分。用户提供视频即可，不把“先装 uv / 配 Python / 理解 MCP”作为使用前提。在已有授权内执行必要配置；系统权限、登录或未授权的安装范围用一句话说明要做什么及原因。已验证可用的环境不重复安装，也不静默升级、替换现有程序。

## Notion

1. 优先复用当前已提供的 Notion 工具。若有 `get_self`，用只读调用验证账号与工作区；没有时可读取用户提供的目标页面。只报告必要的工作区信息，不输出邮箱等无关个人资料。
2. 若未连接且宿主有 plugin-management，搜索 Notion，使用返回的插件标识展示连接入口；已安装则检查连接或权限，不重复建议安装。用户在宿主提供的登录界面完成 OAuth 授权，之后再次只读验证。不要编造按钮名称或连接状态。
3. 没有插件入口但使用 Codex CLI 时，先检查 `codex mcp --help`、`codex mcp add --help`、`codex mcp login --help`。按当前官方文档配置 Notion 远程 MCP。已有同名配置时先确认，不能覆盖别人的服务。

常见 CLI 配置方式（执行前核对本机帮助；添加配置与用户登录是两个步骤）：

```bash
codex mcp add notion --url https://mcp.notion.com/mcp
codex mcp login notion
```

由用户本人在浏览器登录并授权。需要刷新工具列表或新会话时，明确告诉用户下一步；不要因为命令退出成功就认为当前会话已经拥有可用 Notion 工具。无需让用户把密码、token 或 OAuth 回调内容粘到聊天中。

若 Agent 没有浏览器控制，但宿主或 CLI 给出登录链接，让用户在自己的浏览器打开即可；不要求提供浏览器控制权。若既没有可用 Notion 工具、插件入口，也没有可执行的 Codex CLI，则说明当前会话缺少连接能力，给出用户在支持 Notion 连接的 Codex 环境完成授权后继续的路径。不要声称已安装插件或已登录；可先完成本地文章，连接恢复后再保存。用户暂不授权时停止 Notion 分支，不改用他人账号或手动索取 token。

4. 写文章前验证目标页面可读；数据库需要读 schema。只读成功不能证明写权限，实际文章创建成功才证明本次写入成功。
5. 当次指定位置优先；否则检查本用户 `data/settings.md` 中已确认的默认位置。使用保存位置前验证可访问，账号/工作区改变时不可仅凭旧记录继续写入。无保存位置时，支持私人草稿的工具可直接使用私人草稿；其他情况请用户提供自己的父页面链接，不需要先建数据库。用户说“以后都放这里”即授权记住该目标，保存后说明以后会复用，不每次重复询问。

不把个人账号、工作区 ID 或保存位置写进共享 skill。当前会话可复用已给出的目标；只有用户要求持久保存默认位置时才写到 `~/.local/skill-state/video-to-notion/data/settings.md`。OAuth 凭据继续由宿主管理，不复制到该文件。各次任务的文章与页面映射另存 `data/<唯一任务目录>/`，见 [写入与恢复](notion.md)。

参考：[Codex MCP 与 OAuth](https://developers.openai.com/codex/mcp)、[Notion 官方连接指南](https://developers.notion.com/guides/mcp/get-started-with-mcp)。界面或命令不符时重新核对官方文档。

## 视频与转录

需要读取浏览器 Cookie 时，先按 [提取参考](extraction.md) 的登录提示说明可能出现的系统钥匙串窗口及拒绝影响，再启动命令；用户只在系统窗口操作，Agent 不接收密码。音视频下载按该参考的 60 分钟规则判断，模型下载独立处理。

先区分路径：用户已提供可用字幕时可以直接读取；URL 获取字幕需要 `yt-dlp`；提取音频/画面时才需要 `ffmpeg` 和 `ffprobe`；没有可用字幕才检查转录工具。检测命令是否存在并实际执行版本或帮助检查，不能只凭包管理器记录。记录本次选定可执行文件的路径，后续命令复用它；隔离环境中的程序不在 PATH 时使用绝对路径。

缺失的 Python 工具优先安装在 `~/.local/skill-state/video-to-notion/cache/venv/` 的独立环境；优先用已可用的 uv 管理，缺 uv 时由 Agent 按其 [官方安装说明](https://docs.astral.sh/uv/getting-started/installation/) 在授权和权限内配置。已有可用隔离环境则复用，不为统一栈重装。不要要求用户理解环境管理，不修改系统 Python，不在仓库根建立公共依赖。

`ffmpeg` 等系统程序先检查已有可用包管理器及平台支持，再按官方方式安装。没有安装权限、没有可用终端、用户拒绝安装，或环境无法执行所需程序时，停止安装分支，简明提供“给我字幕/可读取的视频”或“换到可运行工具的环境继续”等实际选项；不要换包管理器绕过拒绝。确需新增系统依赖时说明名称、用途和作用范围；已有程序故障时先报告实际错误，升级需有依据和授权，不能运行全局批量升级。

无字幕视频默认使用 SenseVoiceSmall 的 FunASR llama.cpp / GGUF 运行时；先检查已有 `llama-funasr-sensevoice` 及实际平台/架构，不因机器已有 Whisper 就改用它。有字幕且覆盖用户所需范围时不安装转录工具、不下载模型；部分缺失且需要补齐时仅转录缺段，并执行同样的下载前说明。

安装 Python 环境或首次模型下载**之前**用一段短说明列出：选用的实现、模型名称；实际可执行文件/环境安装绝对路径；模型文件保存绝对路径；本次是否下载、已核实的下载体积（无法确认就明确“大小暂无法确认”，不可按模型名字猜测）；计算需求及原始输出长期保存位置。未获得该安装/下载范围授权时再询问，已授权则说明后继续。结束后核对路径并报告，不将计划路径写成已安装路径。

SenseVoice 运行时优先选择 [入口页](https://www.funasr.com/llama-cpp.html) 指向的 [官方 Releases](https://github.com/modelscope/FunASR/releases) 中与系统/架构匹配的 CPU 二进制，放在 `~/.local/skill-state/video-to-notion/cache/runtime/<实际版本>/`。本地推理无需 Python ML 环境；下载辅助脚本可能需要 Bash 与 Hugging Face CLI，二者不能混为一谈。不固定“最新”版本；下载前核对具体资产及上游校验信息，记录实际版本，文件存在不代表已可运行。

模型默认显式放到 `~/.local/skill-state/video-to-notion/cache/models/sensevoice/`。依据 [运行仓库说明](https://github.com/modelscope/FunASR/tree/main/runtime/llama.cpp)，下载脚本支持：

```bash
bash download-funasr-model.sh sensevoice "$MODEL_DIR" q8
```

执行前从对应 runtime 版本取得并检查脚本；默认先选 SenseVoiceSmall q8 加 FSMN-VAD，已有可用同模型其他量化档可复用并记录。脚本可能要求 `hf`：缺失时用 uv 隔离准备 huggingface_hub，或从该版本脚本指定的官方模型仓库下载准确文件，不运行全局 pip 升级。上游模型来源为 Hugging Face 的 [FunAudioLLM/SenseVoiceSmall-GGUF](https://huggingface.co/FunAudioLLM/SenseVoiceSmall-GGUF) 与 [FunAudioLLM/fsmn-vad-GGUF](https://huggingface.co/FunAudioLLM/fsmn-vad-GGUF)；仓库标识及文件名以脚本/发布说明核实，不猜 URL。

入口页列出 SenseVoice encoder q8 约 254 MB、f16 约 470 MB；模型卡另列 q8 约 235 MB，与入口页不同，应以选中文件实际大小为准；VAD 模型卡列约 1.7 MB。这不含运行时及下载缓存，也不代表内存需求。实际下载前核对文件大小，总体积无法核实就明确未知。使用实际模型路径传 `-m` 和 `--vad`，不要依赖默认下载目录。既有模型可原位复用，不强行搬迁；不可确认路径时先查清。

模型、二进制与可重建环境是缓存；`data/<任务目录>/sources/` 的原始字幕/转录长期保留。先验证 `--help` 和必要的短音频流程，测试输出放独立批次；无匹配二进制、下载失败、拒绝下载或 CLI 能力不足时说明具体阻碍，不静默退回 Whisper/其他模型或远程服务。源码编译只有明确需要且授权后进行，不把编译工具当默认首次使用要求。

用户明确选择其他实现或已有并授权远程转录服务时才可改用，先说明上传范围与预计用量。不要把 ChatGPT 或 Codex 订阅等同于已配置语音 API；不索要聊天明文密钥。

成功判断分开报告：程序可启动、短片段转录成功、完整视频处理完成。转录依赖没有就绪时保留现有文件，不能用标题和简介代替正文。
