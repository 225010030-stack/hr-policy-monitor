# 未来操作台网页接入契约

**当前阶段不实现**；新网页做好后按本文对接即可。

## 发现接口

```http
GET /api/meta
```

返回 `endpoints` 字典，含 JSON 与 Bot 文本 URL。

## 前端推荐用的 JSON API

### 资讯墙列表

```http
GET /api/policy-feed?limit=50&region=US&category=leave&min_score=3
```

响应：

```json
{
  "ok": true,
  "synced_at": "2026-06-18T10:32:18",
  "total": 42,
  "items": [
    {
      "id": "...",
      "title": "...",
      "link": "https://...",
      "summary": "...",
      "published_at": "...",
      "region": "US",
      "category": "tax",
      "score": 8,
      "matched_keywords": ["payroll", "tax"],
      "source_name": "US Federal Register · IRS"
    }
  ]
}
```

### 每日早报

```http
GET /api/policy-feed/digest
```

### 每周复盘

```http
GET /api/policy-feed/weekly
```

## 嵌入方式（三选一）

1. **iframe**：`<iframe src="{PUBLIC_BASE_URL}/index.html" />`（临时资讯墙）
2. **fetch + 自绘 UI**：读 `/api/policy-feed`，5 分钟轮询
3. **同域反代**：Nginx 见 `deploy/nginx-snippet.conf`，前端 `fetch('/api/policy-feed')`

## 环境变量（新网页上线时）

```bash
PUBLIC_BASE_URL=https://fpp.example.com/policy
MONITOR_API_TOKEN=          # 可选；仅 POST 同步/触发需要
```

## CORS

服务已 `allow_origins: *`。同域反代时无跨域问题。

## 刷新策略

| 层级 | 频率 |
|------|------|
| GitHub Actions | 每 6h 写 `data/policy-feed.json` |
| 服务端 | 读本地 JSON，无 DB |
| 前端 | 建议 5 分钟 `fetch` 一次 |

## 暂不做的项

- 不修改 `工作提效/web-tool/upload-docs.html`
- 不在 `bot-gateway` 内嵌 RSS 逻辑
- 监控数据仍只维护在 **hr-policy-monitor** 仓库
