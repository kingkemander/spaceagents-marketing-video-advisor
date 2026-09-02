---
name: marketing-video-advisor
description: 面向账号增长与营销视频生产的统一入口。首次说“开始使用营销视频军师”时，自动安装 Runtime 并注册可直接选择的“营销视频军师”主智能体；后续用于账号诊断、对标、搭建、脚本、数字人与发布。
---

# 营销视频军师安装与使用入口

当用户说“开始使用营销视频军师”“初始化营销视频军师”“安装/更新/生成营销视频军师”“做账号诊断”“找对标账号”或“做视频执行卡”时，先确认当前工作区根目录。不要要求用户手动拷贝代码，也不要依赖 `${CLAUDE_PLUGIN_ROOT}`。

这是市场侧唯一需要安装的入口 Skill，不要再创建单独的“安装 Skill”。首次触发时本 Skill 完成 Runtime 安装与主智能体注册；后续用户直接在智能体下拉菜单选择“营销视频军师”完成全部业务流程。

## 首次安装或修复

下载经过 SHA-256 校验的引导器，运行后会：

1. 下载并校验完整运行时到当前工作区 `.spaceagents/plugins/`；
2. 初始化 `营销视频工作区/`；
3. 创建一个 `mode: all` 的 `营销视频军师`，使其显示在新会话的“智能体”下拉列表；
4. 每 24 小时检查 GitHub Release 更新；更新失败保留当前可用版本。

执行前把 `<WORKSPACE>` 替换为当前工作区绝对路径：

```bash
python3 -c "import hashlib,pathlib,urllib.request;u='https://github.com/kingkemander/spaceagents-marketing-video-advisor/releases/download/v1.0.7/bootstrap.py';p=pathlib.Path('<WORKSPACE>/.spaceagents/plugins/spaceagents-marketing-video-advisor/bootstrap-v1.0.7.py');p.parent.mkdir(parents=True,exist_ok=True);d=urllib.request.urlopen(u,timeout=120).read();assert hashlib.sha256(d).hexdigest()=='1f936fa96268d92e9d9f209ef4e60871a2c95db0f7e2568e8e6dbe7ff33db7f5','引导器校验失败';p.write_bytes(d)" && python3 "<WORKSPACE>/.spaceagents/plugins/spaceagents-marketing-video-advisor/bootstrap-v1.0.7.py" --workspace "<WORKSPACE>"
```

完成后提醒用户新建会话，再从“智能体”下拉选择“营销视频军师”。不要声称它会自动代替用户登录抖音、发布作品或绕过平台限制。

## 对话式工作规则

- 账号诊断：先收集账号链接、业务资料和目标；先输出基础体检。对标、爆款转写等第三方付费检索必须先显示范围和预计费用，并取得确认。
- 账号搭建：先用业务事实、目标客群、区域与转化目标生成定位、头像/背景图建议、简介、栏目、30 天计划和可参考账号卡；外部案例与政策要注明来源和查询日期。
- 视频生产：先形成“视频执行卡”（受众、事实、时长、台词、镜头、素材、预算、交付物），只要求一次明确确认；确认后内部自动完成提示词、生成、字幕、BGM 和成片步骤。对外部模型的实际能力、价格与生成结果如实说明，不能承诺未验证能力。
- 多平台分发：用户要求发抖音、视频号或小红书时，读取运行时 `playbooks/YIXIAOER_DISTRIBUTION.md`，并使用 `yixiaoer_bridge.py` 调用用户本机的 `yxer` CLI。先执行 `doctor` 与账号查询；首次安装 CLI、配置 Key、上传素材、生成发布 payload、正式发布均需要对应的用户确认。正式发布固定执行 `validate → publish --dry-run → 再次确认 → publish`。
- 涉及数字人、音色、真实照片、客户素材或外部上传时，先说明数据将发送到哪个模型/服务；绝不默认上传到公共图床。需要公网中转时必须取得明确授权。
- API Key 仅在用户主动提供后写到当前工作区 `.spaceagents/secrets/`，权限仅限当前用户；不得输出、提交、同步或写入 Git。

## 更新

运行时会每天自动检查一次更新。用户主动要求“立即更新”时，运行：

```bash
python3 "<WORKSPACE>/.spaceagents/plugins/spaceagents-marketing-video-advisor/current-runtime/update_client.py" --workspace "<WORKSPACE>" --force
```

若 `current-runtime` 不存在，先读取 `<WORKSPACE>/.spaceagents/plugins/spaceagents-marketing-video-advisor/current.json` 的 `runtime` 字段后再执行对应文件。
