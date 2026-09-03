# 工具链准备工作流

## 必需工具

| 工具 | 用途 | 检查命令 |
|---|---|---|
| Node.js LTS + npm | 运行蚁小二 CLI | `node --version`、`npm --version` |
| 蚁小二 `yxer` CLI | 查询账号、上传、校验、预览和发布 | `yxer doctor` |
| FFmpeg | 后期烧录字幕、混入 BGM、封装视频 | `ffmpeg -version` |

首次使用或执行视频/发布任务前，运行时先执行 `setup_tools.py` 检查。缺失项必须向用户列出后再询问是否安装。

## 安装规则

- macOS：优先使用已安装的 Homebrew 执行 `brew install node ffmpeg`，再执行 `npm install -g @yixiaoermail/cli@latest`；没有 Homebrew 时只提供官方安装链接，不下载未知脚本。
- Windows：优先使用 winget 安装 Node.js LTS 与 FFmpeg，再用 npm 安装 `yxer`；没有 winget 时提示安装 App Installer 或手动安装。
- 安装完成后重新检查四个版本，并执行 `yxer doctor`；任何一步失败都停止，不伪造“已安装”。
- 用户未明确确认时只检查，不安装。安装、全局 npm 包和系统包均属于外部环境变更。
- 不要求用户把蚁小二 API Key、Client ID 或平台凭据发到聊天；凭据只在用户本机按蚁小二说明配置。

## 字幕烧录门禁

没有 FFmpeg 时只能交付无字幕母版，不能声称已完成字幕终版。用户确认安装后，使用 FFmpeg 完成字幕烧录、BGM 混音和封装，并保留原始母版。
