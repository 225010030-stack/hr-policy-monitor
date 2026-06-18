# hr-policy-monitor

独立仓库：**海外薪酬福利政策 RSS 监控**（美洲 + 非美洲），与 FPP/工作提效项目完全分离。

## 功能

| 能力 | 说明 |
|------|------|
| 资讯墙 | 网页每 5 分钟刷新 |
| RSS 同步 | GitHub Actions 每 6 小时，或本地脚本 |
| 每日早报 | 昨日 Top 5（关键词打分）→ 企微/邮件 |
| 每周复盘 | 周一汇总 + SOP 复盘提示 |

## 目录结构

```text
hr-policy-monitor/
├── app/              # FastAPI + 核心逻辑
├── config/           # RSS 源 + 关键词权重
├── data/             # 同步结果 JSON（Actions 会 commit）
├── scripts/          # 命令行同步
├── web/              # 资讯墙静态页
└── .github/workflows/
```

## 本地使用

```bash
cd "/Users/zhangwenjing/Desktop/hr-policy-monitor"

# 安装依赖（首次）
python3 -m pip install -r requirements.txt

# 同步 RSS + 生成早报/周报
python3 scripts/sync_policy_feeds.py --sync --digest --weekly

# 启动网页（默认 http://127.0.0.1:18888）
bash start.sh
```

打开：**http://127.0.0.1:18888/**

## 推送到 GitHub

```bash
cd "/Users/zhangwenjing/Desktop/hr-policy-monitor"
git add .
git commit -m "init: overseas payroll policy monitor"
git remote add origin git@github.com:<你的用户名>/hr-policy-monitor.git
git push -u origin main
```

推送后 Actions 会自动定时同步 `data/*.json`。

## 配置

| 文件 | 用途 |
|------|------|
| `config/policy_sources.json` | 监控哪些 RSS（US/CA/UK/EU…） |
| `config/policy_keywords.json` | leave/payroll/benefits 等打分词 |
| `.env` | 企微/邮件推送（复制 `.env.example`） |

## 企微/邮件 Secrets（GitHub）

- `POLICY_DIGEST_WECOM_USERS`
- `WECOM_CORP_ID` / `WECOM_AGENT_ID` / `WECOM_AGENT_SECRET`
- `POLICY_DIGEST_EMAIL_TO` + `POLICY_SMTP_*`

## API

- `GET /api/health`
- `GET /api/policy-feed?limit=50&region=US&min_score=5`
- `GET /api/policy-feed/digest`
- `GET /api/policy-feed/weekly`
- `POST /api/policy-feed/sync`（可选 `X-Monitor-Token`）

## 与工作提效项目的关系

本仓库**独立运行**，不依赖 `bot-gateway` / `web-tool`。若要在 FPP 网页里嵌入，可用 iframe 或链接到本服务地址。
