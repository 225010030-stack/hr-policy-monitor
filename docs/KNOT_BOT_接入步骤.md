# Knot Bot 接入步骤（政策监控 · 接网页前最后一步）

> 目标：在 Knot 控制台新建 **独立智能体**「薪酬福利政策助手」，Chat 里发「政策早报」等指令 → 调用 `hr-policy-monitor` → 返回 RSS 摘要。  
> **不修改** FPP 的 Anna 智能体、不修改 `upload-docs.html`。

---

## 0. 开始前确认（本机）

```bash
cd "/Users/zhangwenjing/Desktop/hr-policy-monitor"
cp .env.example .env
```

编辑 `.env`（至少一行）：

```bash
KNOT_BOT_TOKEN=请换成一串随机字符
```

启动服务：

```bash
bash start.sh
```

另开终端自检：

```bash
cd "/Users/zhangwenjing/Desktop/hr-policy-monitor"
export KNOT_BOT_TOKEN=你刚设的token
bash scripts/test_knot_webhook.sh
```

预期：`政策早报` 返回 `ok: true` 和早报正文。

健康检查：

```bash
curl -s http://127.0.0.1:18888/api/health
```

---

## 1. Knot 控制台：新建智能体（不要改 Anna）

| 字段 | 建议填写 |
|------|----------|
| 智能体名称 | `薪酬福利政策助手` |
| 工作内容简述 | 海外薪酬福利政策 RSS 资讯：早报、周报、分国别列表 |
| 与 Anna 关系 | **单独新建**，不要和 FPP 账单助手混在一个 Agent 里 |

---

## 2. 粘贴 Prompt

打开文件 **`integrations/PROMPT_政策监控助手.md`**，全文复制到 Knot「智能体开发 → Prompt」。

把其中的：

- `http://127.0.0.1:18888` → 若 Knot 预览在云端，改为 **Knot 工作区能访问的内网 URL**（见第 7 节）
- `{{KNOT_BOT_TOKEN}}` → 与 `.env` 里 `KNOT_BOT_TOKEN` **完全一致**

---

## 3. 配置 Client 工具（核心 · 只需 1 个）

点击 **Client 工具 → 添加**

| 项 | 值 |
|----|-----|
| 工具名称 | `policy_monitor_webhook` |
| 请求方法 | `POST` |
| URL | `http://127.0.0.1:18888/api/webhook/knotbot` |
| Header 1 | `Content-Type: application/json` |
| Header 2 | `X-Bot-Token: <你的 KNOT_BOT_TOKEN>` |
| Body | 见下方 JSON |

Body（复制）：

```json
{
  "text": "{{user_input}}"
}
```

说明：

- `{{user_input}}` 若 Knot 里叫 `{{message}}` / `{{query}}`，改成平台实际变量名
- 服务端也会读 `content` / `query` / `message` 字段，与 FPP `bot-gateway` 一致

参考样例：`integrations/knotbot-webhook-payload.example.json`

---

## 4. 配置 Rules（建议 3 条）

### Rule 1 · 必须调工具

```text
用户消息包含：政策、早报、周报、leave、payroll、benefit、薪酬、福利、FMLA、ADP、Workday 等词时，
必须调用 policy_monitor_webhook，不得自行回答政策内容。
```

### Rule 2 · 只展示 message

```text
工具返回 JSON 后，只向用户展示 message 字段全文，保留链接与序号，不要改写或省略链接。
```

### Rule 3 · 失败回退

```text
若 ok 为 false 或 HTTP 非 200，回复：
「政策服务暂不可用，请稍后重试或发送：政策帮助」
并附带工具返回的 message。
```

---

## 5. 模型设置

- 选 **低成本 / 低推理** 模型（只做关键词路由 + 贴 `message`）
- 不需要 Vision、不需要长上下文

Skills：**可不挂** FPP 的 skill-01/02；政策数据来自 RSS，不是工作区脚本。

---

## 6. 对话测试（右侧测试窗）

按顺序输入，预期 **必须出现 Client 工具调用**：

| 输入 | 预期 action | 预期内容 |
|------|-------------|----------|
| `政策帮助` | policy_help | 指令菜单 |
| `政策早报` | policy_digest | 【薪酬福利政策早报】+ Top 列表 |
| `政策周报` | policy_weekly | 周报 + 复盘提示 |
| `美国政策` | policy_feed_us | US 相关条目 |
| `随便聊聊` | — | ok=false，提示可用指令 |

本地 curl 对照（与 Knot 等价）：

```bash
export KNOT_BOT_TOKEN=你的token
curl -s -X POST "http://127.0.0.1:18888/api/webhook/knotbot" \
  -H "Content-Type: application/json" \
  -H "X-Bot-Token: $KNOT_BOT_TOKEN" \
  -d '{"text":"政策早报"}' | python3 -m json.tool
```

---

## 7. Knot 预览 / 上线 URL 怎么填

| 场景 | Client 工具 URL |
|------|-----------------|
| Knot 与 monitor **同一台 Mac** | `http://127.0.0.1:18888/api/webhook/knotbot` |
| Knot 工蜂预览（同 VPC） | `http://<内网IP>:18888/api/webhook/knotbot` |
| 正式环境 | `https://<你的域名>/policy/api/webhook/knotbot`（Nginx 见 `deploy/nginx-snippet.conf`） |

**注意**：Knot 云端若访问不到你本机 `127.0.0.1`，必须把 monitor 部署到 **Knot 能访问的内网地址**，或在 `.env` 设 `PUBLIC_BASE_URL` 后走统一网关。

与 Anna 的 FPP 网关 **端口分开**：

- Anna → `:18081` / `bot-gateway`
- 政策助手 → `:18888` / `hr-policy-monitor`

---

## 8. 可用指令一览（教同事）

```
政策帮助
政策早报
政策周报
美国政策
加拿大政策
英国政策
最新政策
```

关键词映射表：`config/knot-command-map.json`（可自行增词）

---

## 9. 发布前检查清单

- [ ] `hr-policy-monitor` 已启动（18888 health OK）
- [ ] `.env` 中 `KNOT_BOT_TOKEN` 与 Knot Header 一致
- [ ] Client 工具 URL 从 Knot 环境 **可 curl 通**
- [ ] 测试窗 5 条指令均返回 `message`
- [ ] 与 Anna 分为 **两个** 智能体/入口，避免混指令
- [ ] GitHub Actions 至少成功 sync 过一次（`data/policy-feed.json` 有数据）
- [ ] 点击 Knot **发布更新**

---

## 10. 常见问题

### Q1: 401 Invalid bot token

- Knot 的 `X-Bot-Token` 与 `.env` 的 `KNOT_BOT_TOKEN` 不一致
- 或未重启 `start.sh` 就读取了旧 `.env`

### Q2: Knot 调不通 127.0.0.1

- 预览跑在远端容器，127.0.0.1 指向容器自身
- 改内网 IP 或部署到工蜂可访问的服务

### Q3: 早报为空

- 先 GitHub Actions Run workflow → sync
- 或本地 `python3 scripts/sync_policy_feeds.py --sync --digest`

### Q4: 和 Anna 搞混

- 政策助手单独 Agent；FPP 指令仍走 Anna + bot-gateway

### Q5: 想加新指令

1. 编辑 `config/knot-command-map.json`
2. 重启 monitor
3. Prompt / Rule 里补一句关键词说明

---

## 11. 接新操作台网页（下一步，现在不做）

Bot 接好后，新网页只需 `fetch` JSON API，见 `docs/WEB_INTEGRATION.md`。  
Bot 与网页 **共用同一后端** `hr-policy-monitor`，无需再改 Knot。

---

## 附录 · 返回 JSON 格式

与 FPP `bot-gateway` 一致：

```json
{
  "ok": true,
  "action": "policy_digest",
  "message": "【薪酬福利政策早报】2026-06-17\n...",
  "data": {
    "kind": "digest"
  }
}
```

Knot 展示 **`message`** 即可。
