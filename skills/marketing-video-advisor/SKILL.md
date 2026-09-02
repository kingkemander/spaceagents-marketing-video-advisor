---
name: marketing-video-advisor
description: 安装、更新或使用“营销视频军师”。适用于账号诊断、对标账号、账号搭建、选题脚本、数字人宣传片、视频执行卡、抖音内容规划等请求。
---

# 营销视频军师安装与使用入口

当用户说“安装/更新/生成营销视频军师”“做账号诊断”“找对标账号”“做视频执行卡”时，先确认当前工作区根目录。不要要求用户手动拷贝代码，也不要依赖 `${CLAUDE_PLUGIN_ROOT}`。

## 首次安装或修复

下载经过 SHA-256 校验的引导器，运行后会：

1. 下载并校验完整运行时到当前工作区 `.spaceagents/plugins/`；
2. 初始化 `营销视频工作区/`；
3. 创建一个 `mode: all` 的 `营销视频军师`，使其显示在新会话的“智能体”下拉列表；
4. 每 24 小时检查 GitHub Release 更新；更新失败保留当前可用版本。

执行前把 `<WORKSPACE>` 替换为当前工作区绝对路径：

```bash
python3 -c "import hashlib,pathlib,urllib.request;u='https://github.com/kingkemander/spaceagents-marketing-video-advisor/releases/download/v1.0.2/bootstrap.py';p=pathlib.Path('<WORKSPACE>/.spaceagents/plugins/spaceagents-marketing-video-advisor/bootstrap-v1.0.2.py');p.parent.mkdir(parents=True,exist_ok=True);d=urllib.request.urlopen(u,timeout=120).read();assert hashlib.sha256(d).hexdigest()=='975312d14fae9f168a66b4de1598f867e52f115c3c53b6627e04252587c3d638','引导器校验失败';p.write_bytes(d)" && python3 "<WORKSPACE>/.spaceagents/plugins/spaceagents-marketing-video-advisor/bootstrap-v1.0.2.py" --workspace "<WORKSPACE>"
```

完成后提醒用户新建会话，再从“智能体”下拉选择“营销视频军师”。不要声称它会自动代替用户登录抖音、发布作品或绕过平台限制。

## 对话式工作规则

- 账号诊断：先收集账号链接、业务资料和目标；先输出基础体检。对标、爆款转写等第三方付费检索必须先显示范围和预计费用，并取得确认。
- 账号搭建：先用业务事实、目标客群、区域与转化目标生成定位、头像/背景图建议、简介、栏目、30 天计划和可参考账号卡；外部案例与政策要注明来源和查询日期。
- 视频生产：先形成“视频执行卡”（受众、事实、时长、台词、镜头、素材、预算、交付物），只要求一次明确确认；确认后内部自动完成提示词、生成、字幕、BGM 和成片步骤。对外部模型的实际能力、价格与生成结果如实说明，不能承诺未验证能力。
- 涉及数字人、音色、真实照片、客户素材或外部上传时，先说明数据将发送到哪个模型/服务；绝不默认上传到公共图床。需要公网中转时必须取得明确授权。
- API Key 仅在用户主动提供后写到当前工作区 `.spaceagents/secrets/`，权限仅限当前用户；不得输出、提交、同步或写入 Git。

## 更新

运行时会每天自动检查一次更新。用户主动要求“立即更新”时，运行：

```bash
python3 "<WORKSPACE>/.spaceagents/plugins/spaceagents-marketing-video-advisor/current-runtime/update_client.py" --workspace "<WORKSPACE>" --force
```

若 `current-runtime` 不存在，先读取 `<WORKSPACE>/.spaceagents/plugins/spaceagents-marketing-video-advisor/current.json` 的 `runtime` 字段后再执行对应文件。
