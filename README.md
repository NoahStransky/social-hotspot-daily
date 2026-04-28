# 🌍 Social Hotspot Daily

> 每日全球科技热点聚合，专为 IT / AI 从业者打造

## ✨ Features

- 🤖 **AI 智能筛选** — 用 LLM 自动识别 AI/编程/安全/硬件类新闻
- 🌐 **多平台覆盖** — Twitter, Reddit, Hacker News, YouTube, 微博, 知乎, RSS
- 📰 **自动博客生成** — 生成漂亮的暗色主题静态博客，部署到 GitHub Pages
- 📱 **Telegram 推送** — 每天早上推送精选摘要 + 博客链接
- 🔥 **热度算法** — 综合点赞、评论、转发、观看量计算热点分数
- 💡 **Insight 洞察** — AI 生成 "Why it matters" 专业解读

## 🚀 Quick Start

### 1. Fork / Clone

```bash
git clone https://github.com/YOUR_USERNAME/social-hotspot-daily.git
cd social-hotspot-daily
```

### 2. Configure

复制配置文件并填入 API keys：

```bash
cp config.yaml config.yaml  # 直接编辑
```

需要的环境变量（或填入 config.yaml）：

| 变量 | 用途 | 获取方式 |
|------|------|---------|
| `DEEPSEEK_API_KEY` | AI 分类摘要 | [platform.deepseek.com](https://platform.deepseek.com) |
| `TWITTER_BEARER_TOKEN` | X/Twitter | [developer.twitter.com](https://developer.twitter.com) |
| `REDDIT_CLIENT_ID/SECRET` | Reddit | [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) |
| `YOUTUBE_API_KEY` | YouTube | [Google Cloud Console](https://console.cloud.google.com) |
| `TELEGRAM_BOT_TOKEN` | 推送 | [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | 接收人 | 向 Bot 发消息后用 API 查 |

> 💡 **微博、知乎、Hacker News 不需要 API key**

### 3. Local Test

```bash
pip install -r requirements.txt
python main.py
```

输出在 `docs/` 目录，用浏览器打开 `docs/index.html`。

### 4. GitHub Actions 自动部署

1. 在 GitHub Repo → Settings → Secrets → Actions 中添加所有 secrets
2. 在 Repo → Settings → Pages → Source 选择 "GitHub Actions"
3. 每天早上 8 点 UTC 自动运行，或手动触发

博客地址：`https://YOUR_USERNAME.github.io/social-hotspot-daily/`

## 📁 Project Structure

```
├── collectors/          # 各平台采集器
├── processors/          # 去重 + AI 过滤
├── publishers/          # 博客生成 + Telegram
├── templates/           # HTML 模板
├── docs/                # GitHub Pages 输出
├── main.py              # 入口
└── config.yaml          # 配置
```

## ⚙️ Customization

编辑 `config.yaml`：

- `sources.*.enabled` — 开关某个平台
- `ai_filter.categories` — 调整保留的新闻类别
- `sources.rss.feeds` — 添加你喜欢的 RSS 源
- `output.blog.title` — 博客标题

## 📄 License

MIT
