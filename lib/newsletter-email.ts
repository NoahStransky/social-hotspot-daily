/**
 * Newsletter email template — renders daily news items + analysis into HTML.
 * Data is fetched by the send-newsletter API route and passed here.
 */

interface NewsletterItem {
  title: string;
  url: string;
  summary: string | null;
  insight: string | null;
  source_name: string;
  source_display: string | null;
  category: string;
  score: number;
}

interface NewsletterAnalysis {
  top_topic: string | null;
  top_stories: string | null;
}

export function buildNewsletterHtml(params: {
  date: string;
  items: NewsletterItem[];
  analysis: NewsletterAnalysis | null;
  blogBaseUrl: string;
  unsubscribeUrl: string;
}): string {
  const { date, items, analysis, blogBaseUrl, unsubscribeUrl } = params;

  const formattedDate = formatDate(date);
  const topItems = items.slice(0, 15); // Top 15 items max

  // Category grouping
  const categories = groupBy(topItems, (item) => item.category || "other");

  const analysisHtml = analysis?.top_topic
    ? `
    <div class="analysis-card">
      <h2>📊 今日趋势分析</h2>
      <p class="topic">${escapeHtml(analysis.top_topic)}</p>
      ${analysis.top_stories
        ? `<div class="top-stories">
             <h3>🔥 热门话题</h3>
             <ul>
               ${JSON.parse(analysis.top_stories)
                 .map((s: string) => `<li>${escapeHtml(s)}</li>`)
                 .join("")}
             </ul>
           </div>`
        : ""}
    </div>`
    : "";

  const itemsHtml = Object.entries(categories)
    .map(
      ([cat, catItems]) => `
    <div class="category-section">
      <h3 class="category-title">${escapeHtml(catName(cat))}</h3>
      ${catItems
        .map(
          (item, idx) => `
        <div class="news-item">
          <span class="item-number">${idx + 1}</span>
          <div class="item-content">
            <a href="${escapeHtml(item.url)}" class="item-title" target="_blank">
              ${escapeHtml(item.title)}
            </a>
            <div class="item-meta">
              <span class="source">${escapeHtml(item.source_display || item.source_name)}</span>
              <span class="score">⚡ ${item.score}</span>
            </div>
            ${item.summary ? `<p class="summary">${escapeHtml(item.summary)}</p>` : ""}
            ${item.insight ? `<p class="insight">💡 ${escapeHtml(item.insight)}</p>` : ""}
          </div>
        </div>`
        )
        .join("")}
    </div>`
    )
    .join("");

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Tech Hotspot Daily — ${formattedDate}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
      background: #0a0a0f;
      color: #e2e2f0;
      padding: 20px;
    }
    .container {
      max-width: 640px;
      margin: 0 auto;
      background: #12121a;
      border: 1px solid #252535;
      border-radius: 12px;
      overflow: hidden;
    }
    .header {
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      padding: 32px 28px;
      border-bottom: 1px solid #252535;
      text-align: center;
    }
    .header h1 {
      font-size: 22px;
      color: #6366f1;
      margin-bottom: 4px;
    }
    .header .subtitle {
      font-size: 13px;
      color: #8b8ba7;
    }
    .header .date {
      font-size: 14px;
      color: #a5a5c0;
      margin-top: 8px;
    }
    .body-content {
      padding: 24px 28px;
    }
    .analysis-card {
      background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%);
      border: 1px solid #312e81;
      border-radius: 10px;
      padding: 20px;
      margin-bottom: 24px;
    }
    .analysis-card h2 {
      font-size: 16px;
      color: #818cf8;
      margin-bottom: 10px;
    }
    .analysis-card .topic {
      font-size: 15px;
      line-height: 1.5;
      color: #c7d2fe;
    }
    .analysis-card .top-stories {
      margin-top: 14px;
      padding-top: 14px;
      border-top: 1px solid #312e81;
    }
    .analysis-card .top-stories h3 {
      font-size: 13px;
      color: #818cf8;
      margin-bottom: 8px;
    }
    .analysis-card .top-stories ul {
      padding-left: 18px;
    }
    .analysis-card .top-stories li {
      font-size: 13px;
      color: #a5b4fc;
      margin-bottom: 4px;
      line-height: 1.4;
    }
    .category-section {
      margin-bottom: 20px;
    }
    .category-title {
      font-size: 14px;
      color: #818cf8;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 12px;
      padding-bottom: 6px;
      border-bottom: 1px solid #1e1e30;
    }
    .news-item {
      display: flex;
      gap: 12px;
      padding: 12px 0;
      border-bottom: 1px solid #1a1a28;
    }
    .news-item:last-child {
      border-bottom: none;
    }
    .item-number {
      flex-shrink: 0;
      width: 24px;
      height: 24px;
      background: #1e1e30;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      font-weight: 600;
      color: #6366f1;
    }
    .item-content {
      flex: 1;
      min-width: 0;
    }
    .item-title {
      font-size: 14px;
      font-weight: 600;
      color: #e0e0ff;
      text-decoration: none;
      line-height: 1.4;
      display: block;
    }
    .item-title:hover {
      color: #818cf8;
    }
    .item-meta {
      display: flex;
      gap: 10px;
      margin-top: 4px;
      font-size: 12px;
    }
    .source {
      color: #6b7280;
    }
    .score {
      color: #f59e0b;
    }
    .summary {
      font-size: 12px;
      color: #9ca3af;
      margin-top: 4px;
      line-height: 1.4;
    }
    .insight {
      font-size: 12px;
      color: #a78bfa;
      margin-top: 3px;
      font-style: italic;
      line-height: 1.4;
    }
    .footer {
      padding: 20px 28px;
      border-top: 1px solid #252535;
      text-align: center;
      font-size: 12px;
      color: #6b7280;
    }
    .footer a {
      color: #6366f1;
      text-decoration: none;
    }
    .footer a:hover {
      text-decoration: underline;
    }
    .view-online {
      padding: 16px 28px 0;
      text-align: center;
    }
    .view-online a {
      font-size: 13px;
      color: #818cf8;
      text-decoration: underline;
    }
    @media (prefers-color-scheme: light) {
      body { background: #f5f5f5; }
      .container { background: #ffffff; border-color: #e0e0e0; }
      .header { background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%); border-color: #e0e0e0; }
      .header h1 { color: #4f46e5; }
      .header .subtitle { color: #6b7280; }
      .header .date { color: #6b7280; }
      .analysis-card { background: #f5f3ff; border-color: #c7d2fe; }
      .analysis-card h2 { color: #6366f1; }
      .analysis-card .topic { color: #4338ca; }
      .analysis-card .top-stories { border-color: #c7d2fe; }
      .analysis-card .top-stories li { color: #4f46e5; }
      .category-title { color: #6366f1; border-color: #e0e0e0; }
      .item-number { background: #eef2ff; color: #6366f1; }
      .item-title { color: #1f2937; }
      .summary { color: #6b7280; }
      .insight { color: #7c3aed; }
      .footer { border-color: #e0e0e0; color: #9ca3af; }
      .view-online a { color: #6366f1; }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🚀 Tech Hotspot Daily</h1>
      <p class="subtitle">为你精选每日科技热点</p>
      <p class="date">${formattedDate}</p>
    </div>

    <div class="body-content">
      <p style="font-size:13px;color:#8b8ba7;margin-bottom:20px;">
        共收录 <strong style="color:#e2e2f0;">${items.length}</strong> 条资讯
      </p>

      ${analysisHtml}
      ${itemsHtml}
    </div>

    <div class="view-online">
      <a href="${escapeHtml(blogBaseUrl)}">📖 查看网页版</a>
    </div>

    <div class="footer">
      <p>Tech Hotspot Daily — 为 IT 专业人士精选的每日科技资讯</p>
      <p style="margin-top:6px;">
        <a href="${escapeHtml(unsubscribeUrl)}">取消订阅</a>
      </p>
    </div>
  </div>
</body>
</html>`;
}

// ─── Helpers ──────────────────────────────────────────────────────────

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00Z");
  return d.toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
    timeZone: "UTC",
  });
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function groupBy<T>(items: T[], keyFn: (item: T) => string): Record<string, T[]> {
  const map: Record<string, T[]> = {};
  for (const item of items) {
    const key = keyFn(item);
    if (!map[key]) map[key] = [];
    map[key].push(item);
  }
  return map;
}

function catName(cat: string): string {
  const names: Record<string, string> = {
    ai: "🤖 AI 人工智能",
    tech: "💻 科技前沿",
    programming: "👨‍💻 编程开发",
    startup: "🚀 创业投资",
    security: "🔒 安全",
    science: "🔬 科学",
    mobile: "📱 移动设备",
    cloud: "☁️ 云计算",
    blockchain: "⛓️ 区块链",
    gaming: "🎮 游戏",
    other: "📰 其他资讯",
  };
  return names[cat] || cat;
}
