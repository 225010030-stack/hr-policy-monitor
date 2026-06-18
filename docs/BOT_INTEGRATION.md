# Bot 接入说明（Knot / 企微 / webhook）

**不修改** FPP 操作台或 `bot-gateway` 源码；Bot 直接 HTTP 调用本服务。

## 服务地址

| 环境 | Base URL |
|------|----------|
| 本地 | `http://127.0.0.1:18888` |
| 上线 | `.env` 里 `PUBLIC_BASE_URL`，如 `https://fpp.example.com/policy` |

## 推荐给 Bot 用的接口（纯文本）

| 接口 | 用途 |
|------|------|
| `GET /api/bot/digest?format=text` | 每日早报 Top5 |
| `GET /api/bot/weekly?format=text` | 每周复盘 |
| `GET /api/bot/feed?format=text&region=US&min_score=5&limit=10` | 资讯列表摘要 |

JSON 版（去掉 `format=text`）返回 `{ "ok": true, "text": "..." }`，便于 Client 工具解析。

## Knot Client 工具示例

- 方法：`GET`
- URL：`http://127.0.0.1:18888/api/bot/digest?format=text`
- 完整 JSON 模板见：`integrations/knot-client-tool.example.json`

Agent Prompt 片段：

```text
用户问「政策早报」「薪酬政策更新」「leave 有什么新闻」时：
- 早报 → 调用 policy_monitor_digest
- 周报 → GET .../api/bot/weekly?format=text
- 按国家筛选 → GET .../api/bot/feed?format=text&region=US&min_score=5
把返回的 text 直接回复，不要编造链接。
```

## 企微自动推送（无需 Bot 对话）

在 **GitHub Actions Secrets** 配置：

- `POLICY_DIGEST_WECOM_USERS`
- `WECOM_CORP_ID` / `WECOM_AGENT_ID` / `WECOM_AGENT_SECRET`

Actions 每日 `digest` job 会自动 `--notify`。

本地测试推送：

```bash
cp .env.example .env   # 填企微变量
python3 scripts/sync_policy_feeds.py --digest --notify
```

## 与 bot-gateway 的关系

| 方案 | 说明 |
|------|------|
| **A. 直接调 monitor（推荐）** | Knot Client → `18888/api/bot/*`，零改 FPP |
| **B. 以后 gateway 代理** | 新操作台阶段再在 gateway 加转发，非现在 |

## 自检

```bash
bash scripts/verify_service.sh
curl -s "http://127.0.0.1:18888/api/bot/digest?format=text"
```
