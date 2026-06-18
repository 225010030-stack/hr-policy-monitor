# 接入准备清单（加网页 / 接 Bot 之前）

完成下列项后，再在新操作台里嵌 iframe 或 fetch API。

## 一、GitHub / 数据

- [x] 仓库：https://github.com/225010030-stack/hr-policy-monitor
- [x] Actions **Policy Feed Sync** 至少成功跑过一次
- [ ] GitHub Secrets（可选）：企微/邮件 `POLICY_DIGEST_*`、`WECOM_*`、`POLICY_SMTP_*`
- [ ] 按需编辑 `config/policy_sources.json`（加 SG/MY/JP、ADP Release Notes 等）
- [ ] 按需编辑 `config/policy_keywords.json`（业务关键词）

## 二、本机服务

```bash
cd "/Users/zhangwenjing/Desktop/hr-policy-monitor"
cp .env.example .env          # 按需填写
python3 -m pip install -r requirements.txt
git pull                      # 拉 Actions 写入的 data/*.json
bash start.sh                 # 开发：http://127.0.0.1:18888
bash scripts/verify_service.sh
```

生产常驻（可选）：

```bash
bash deploy/start-production.sh
# 或安装 deploy/com.hr.policy-monitor.plist 到 ~/Library/LaunchAgents/
```

## 三、Knot Bot 接入（接网页前最后一步）✅ 已实现

**逐屏操作文档（必读）**：[`docs/KNOT_BOT_接入步骤.md`](docs/KNOT_BOT_接入步骤.md)

快速联调：

```bash
cp .env.example .env    # 设置 KNOT_BOT_TOKEN
bash start.sh
export KNOT_BOT_TOKEN=你的token
bash scripts/test_knot_webhook.sh
```

| 复制粘贴文件 | 用途 |
|--------------|------|
| `integrations/PROMPT_政策监控助手.md` | Knot Prompt |
| `integrations/knot-client-tool.example.json` | Client 工具字段对照 |
| `config/knot-command-map.json` | 指令关键词映射 |

## 四、Bot 直连 API（不用 webhook 时）

| 用户说法 | 调用 |
|----------|------|
| 政策早报 / 今日政策 | `GET /api/bot/digest?format=text` |
| 政策周报 | `GET /api/bot/weekly?format=text` |
| 美国 leave 相关 | `GET /api/bot/feed?format=text&region=US&min_score=5` |

Knot 配置参考：`integrations/knot-client-tool.example.json`  
详细说明：`docs/BOT_INTEGRATION.md`

## 四、未来操作台网页（现在不做）

新网页做好后只需：

1. 设置 `PUBLIC_BASE_URL`（`.env`）
2. Nginx 参考 `deploy/nginx-snippet.conf`
3. 前端 `fetch('/api/policy-feed')` 或 iframe `/policy/index.html`
4. 发现接口：`GET /api/meta`

契约文档：`docs/WEB_INTEGRATION.md`

## 五、验证命令

```bash
curl -s http://127.0.0.1:18888/api/meta | python3 -m json.tool
curl -s "http://127.0.0.1:18888/api/bot/digest?format=text"
curl -s "http://127.0.0.1:18888/api/policy-feed?limit=3&min_score=5"
```

全部 OK 即表示「加网页前准备」已完成。
