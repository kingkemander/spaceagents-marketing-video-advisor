# SpaceAgents 营销视频军师

面向抖音、视频号和小红书的对话式账号增长与营销视频生产插件。

## 安装

在 SpaceAgents 扩展中心选择“从 GitHub 安装”，输入：

```text
https://github.com/kingkemander/spaceagents-marketing-video-advisor
```

安装后新建或打开一个工作区，说：

> 生成营销视频军师

插件会把可直接选择的“营销视频军师”写入该工作区的 `.opencode/agents/营销视频军师.md`。不绑定开发者电脑、不写死模型；后续每 24 小时最多检查一次稳定更新。

## 主要能力

- 账号战略卡、账号体检、对标账号与爆款结构拆解
- 昵称、简介、头像/背景方案、置顶内容与 30 天内容计划
- 视频执行卡、数字人/多参考生视频、自动字幕和 BGM 后处理
- 公开数据报告和发布前合规检查

## 视频模型通道

- 生视频统一调用 SpaceAgents AutoApi：`https://token.spaceagents.cn/v1/chat/completions`。
- 默认模型为 `wan3.0-video`；认证只读取 `SPACEAGENTS_AUTO_API_KEY`（或临时的 `AUTOAPI_API_KEY`），不写入本地配置、Git 或日志。
- 先确认执行卡、素材范围与成本，再提交生成；模型完成后下载原片，并可自动烧录字幕和混入授权 BGM。

## 隐私与费用

- API Key 仅由 SpaceAgents 环境变量或用户本机临时配置提供；仓库不含任何可用密钥。
- 抖音数据与视频生成可能按次或按秒计费，智能体必须在执行前获得用户确认。
- 默认不上传素材到第三方公开图床；如某服务要求外部素材 URL，必须单独征得确认。
