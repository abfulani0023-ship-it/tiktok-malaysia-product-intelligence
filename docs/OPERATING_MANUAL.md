# Amazon to TikTok Malaysia 选品运营手册

## 每日选品流程

1. 从 Amazon US / SG / UK 的 Best Sellers、Movers & Shakers、New Releases 或选品工具导出候选商品。
2. 过滤明显不适合 TikTok 马来西亚的商品：大件、易碎、侵权、医疗夸大、售后复杂。
3. 把候选商品填入 `data/amazon_products.csv`。
4. 运行：

```bash
python3 src/run_pipeline.py
```

5. 优先查看图文看板 `outputs/visual_product_report.html`，再查看明细表 `outputs/ranked_products.csv`。
6. 对 `scale-test` 和 `test` 商品制作脚本和素材。
7. 每个商品至少测试 10-20 条视频，不用单条视频判断商品死活。
8. 把 TikTok 竞品视频和自家视频表现记录到 `data/tiktok_competitor_videos.csv`。
9. 把最终选品决策记录到 `data/product_decisions.csv`。

## Amazon 商品字段说明

| 字段 | 含义 |
|---|---|
| `product_id` | 自定义商品编号，例如 P001 |
| `source` | 数据来源，例如 amazon、helium10、manual |
| `asin` | Amazon ASIN |
| `marketplace` | Amazon 站点，默认只使用 US、SG、UK |
| `category` | 商品类目 |
| `title` | 商品标题 |
| `price_usd` | 美元价格，脚本会估算马币 |
| `rating` | 星级 |
| `review_count` | 评论数 |
| `bsr_rank` | Best Sellers Rank，越小越好 |
| `monthly_sales_est` | 月销量估算 |
| `review_growth_30d` | 近 30 天评论增长百分比 |
| `price_drop_pct` | 近期降价百分比 |
| `bullet_points` | 卖点，多个卖点用分号隔开 |
| `top_review_pain_points` | 评论痛点，多个痛点用分号隔开 |
| `manual_visual_score` | 视频可视化程度，1-5 分 |
| `manual_malaysia_fit_score` | 马来西亚适配度，1-5 分 |
| `manual_competition_risk` | 竞争风险，1-5 分，越高越危险 |
| `manual_logistics_risk` | 物流售后风险，1-5 分，越高越危险 |
| `manual_compliance_risk` | 合规风险，1-5 分，越高越危险 |

## 人工评分建议

`manual_visual_score`：

- 5 分：一眼能看出前后变化，适合 before/after
- 4 分：使用过程清楚，适合演示
- 3 分：需要解释，但还能拍
- 2 分：视觉效果弱
- 1 分：几乎只能讲功能

`manual_malaysia_fit_score`：

- 5 分：强本地场景，例如湿热、雨季、小户型、办公室、车内、厨房
- 4 分：普遍刚需，价格适中
- 3 分：有需求但不够本地化
- 2 分：需求弱
- 1 分：马来西亚场景不明显

## TikTok 内容测试规则

每个商品至少做 4 类脚本：

1. 痛点解决：problem -> product -> result
2. 对比测试：old way vs new way
3. 本地场景：Malaysia weather / small condo / office / car / kitchen
4. 评论回复：回答用户最担心的问题

判断顺序：

1. 低播放：先改前 3 秒 hook
2. 播放高但点击低：改商品利益点和 CTA
3. 点击高但不成交：查价格、评价、商品页、物流承诺
4. 成交高：围绕同痛点批量生成变体
