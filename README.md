# hr-policy-monitor

独立仓库：**海外薪酬福利政策 RSS 监控**。与 FPP / 工作提效 **完全分离**。

> **当前阶段**：服务 + Bot API + GitHub Actions 已就绪；**尚未**接入旧操作台网页。  
> 接入前清单：`docs/PRE_INTEGRATION_CHECKLIST.md`

## 功能

| 能力 | 状态 |
|------|------|
| RSS 同步（Actions 每 6h） | ✅ |
| 临时资讯墙 `web/index.html` | ✅ |
| Bot 纯文本 API `/api/bot/*` | ✅ |
| **Knot Bot webhook** `/api/webhook/knotbot` | ✅ |
| 企微/邮件早报（Secrets） | 待配置 |
| 新操作台嵌入 | 📋 见 `docs/WEB_INTEGRATION.md` |

## 目录

```text
hr-policy-monitor/
├── app/                 # FastAPI + RSS 逻辑 + bot 文本格式
├── config/              # RSS 源、关键词
├── data/                # Actions 写入的 JSON
├── docs/                # 接入文档（Bot / 未来网页）
├── deploy/              # 生产启动、Nginx、LaunchAgent
├── integrations/        # Knot Client 工具示例
├── scripts/             # sync、verify
└── web/                 # 临时资讯墙（新网页做好前自用）
```

## 快速开始

```bash
cd "/Users/zhangwenjing/Desktop/hr-policy-monitor"
python3 -m pip install -r requirements.txt
git pull
bash start.sh
bash scripts/verify_service.sh
```

- 资讯墙：http://127.0.0.1:18888/
- 接口发现：http://127.0.0.1:18888/api/meta

## Knot Bot 接入（接网页前 · 最后一步）

**逐屏文档**：[`docs/KNOT_BOT_接入步骤.md`](docs/KNOT_BOT_接入步骤.md)

| 复制到 Knot 控制台 | 文件 |
|--------------------|------|
| Prompt | `integrations/PROMPT_政策监控助手.md` |
| Client 工具对照 | `integrations/knot-client-tool.example.json` |

```bash
cp .env.example .env          # 填 KNOT_BOT_TOKEN=随机字符串
bash start.sh
export KNOT_BOT_TOKEN=你的token
bash scripts/test_knot_webhook.sh
```

## Bot 直连 API（可选）

```bash
curl -s "http://127.0.0.1:18888/api/bot/digest?format=text"
```

详见 `docs/BOT_INTEGRATION.md`

## GitHub

https://github.com/225010030-stack/hr-policy-monitor

Actions：**Policy Feed Sync**（手动 Run workflow → `sync` / `all`）

## 未来操作台

**现在不改** `upload-docs.html`。新网页做好后按 `docs/WEB_INTEGRATION.md` + `deploy/nginx-snippet.conf` 对接。

## API 摘要

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/meta` | 接入发现 |
| GET | `/api/policy-feed` | JSON 资讯列表 |
| GET | `/api/policy-feed/digest` | JSON 早报 |
| GET | `/api/bot/digest?format=text` | Bot 早报纯文本 |
| GET | `/api/bot/weekly?format=text` | Bot 周报纯文本 |
| GET | `/api/bot/feed?format=text` | Bot 资讯摘要 |
| POST | `/api/webhook/knotbot` | **Knot Client 工具**（Body: `{"text":"政策早报"}`） |
