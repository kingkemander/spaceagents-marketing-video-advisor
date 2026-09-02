# 蚁小二多平台分发工作流

## 适用请求

“把成片发到抖音/视频号/小红书”“多平台发布”“先存草稿”“查看发布状态”。

## 前置条件

1. 用户在自己的电脑安装并登录蚁小二客户端，完成目标平台账号授权；
2. 用户明确同意安装 `yxer` CLI 后，才能执行 `npm install -g @yixiaoermail/cli@latest`；
3. 用户使用自己的蚁小二 API Key 和本机 Client ID 配置 CLI。不得把其 Key、Client ID 或账号信息写入本插件、Git 或共享工作区。

## 固定调用链

```text
yxer doctor
  → yxer accounts list <platform> --status 1
  → yxer upload <video/cover>
  → yxer schema / prepare（按平台实际字段生成 payload）
  → yxer validate <platform> video payload.json
  → yxer publish video <platform> payload.json --dry-run
  → 用户确认账号、标题、文案、素材、时间和平台
  → yxer publish video <platform> payload.json
  → yxer query records / content-overviews
```

## 规则

- 只通过 `yxer` CLI 发布，不手写或绕过蚁小二 API。
- `validate` 与 `--dry-run` 使用同一份 payload 和同一发布通道；正式发布前必须展示预览结果。
- 动态字段（话题、定位、音乐、合集、商品等）先用 CLI 查询，不能臆造 ID。
- 不能因素材已经生成就自动发布；每一次正式发布必须单独获得用户确认。
- 蚁小二 CLI 不提供评论/私信回复能力；这部分只能由客户端功能或其他经授权的渠道处理。
