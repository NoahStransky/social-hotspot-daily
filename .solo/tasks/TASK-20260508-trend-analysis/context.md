需要给 social-hotspot-daily 项目增加 AI 趋势分析和推荐阅读功能。

## 背景
项目目前已有一个 AIFilter 类，对每条新闻做逐条处理（分类、摘要、insight、relevance_score）。这些结果存储在 archive JSON 中。

但缺少**全局维度的分析**：
1. 每天的整体趋势分析（热点话题、分类占比趋势）
2. 推荐阅读排序（must_read / recommended / notable 三级）
3. 跨日对比（"相比昨天，今天有什么变化"）

## 技术现状
- 项目路径: /opt/data/home/social-hotspot-daily/
- 采集流程: main.py → collectors → processors/ai_filter.py → publishers/blog_generator.py
- AI 调用: 通过 DeepSeek API，batch 方式（每15条一组）
- 数据存储: archive JSON (docs/archive/YYYY/MM/DD/index.json)，包含 items 数组
- 博客模板: templates/blog.html (Jinja2 渲染 + SPA JS)
- GitHub Pages 部署: 静态页面

## 数据示例
archive JSON 当前结构:
```json
{
  "date": "2026-05-07",
  "items": [
    {
      "title": "...",
      "url": "...",
      "source": "techcrunch.com",
      "category": "artificial_intelligence",
      "summary": "...",
      "insight": "...",
      "english_title": "..."
    }
  ]
}
```

## 需求
1. 新增 trend_analysis 字段到 archive JSON（与 items 并列）
2. 每条新闻增加 recommendation 字段（level: must_read/recommended/notable）
3. 博客页面展示趋势面板 + 推荐排序
4. Telegram 通知加入趋势摘要
5. 保持向后兼容（已有 archive JSON 不受影响）
