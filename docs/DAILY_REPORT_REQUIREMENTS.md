# 每日跨境选品日报需求定义

## 固定口径

- 目标市场：TikTok Malaysia
- 监控站点：Amazon US / Amazon SG / Amazon UK
- 核心假设：Amazon US / SG / UK 能爆或即将爆的品，优先进入 TikTok Malaysia 测试池
- 发送时间：每天 09:00，Asia/Shanghai 与 Malaysia 同为 UTC+8

## 每日抓取目标

1. 热门品类
2. 上升最快品类
3. 品类对应商品
4. 商品评分与评论数量
5. 用户评论关键词
6. 正向标签与负向标签
7. 基于差评的产品机会
8. TikTok Malaysia 测试建议

## 商品字段

| 字段 | 说明 |
|---|---|
| product_id | 商品编号 |
| marketplace | US / SG / UK |
| category | Amazon 类目 |
| title | 商品标题 |
| price | 原站价格 |
| price_myr_est | 估算马币价格 |
| rating | 用户评分 |
| review_count | 评论数量 |
| trend_signal | 热门/上升依据 |
| positive_tags | 正向评论标签 |
| negative_tags | 负向评论标签 |
| negative_review_summary | 差评摘要 |
| opportunity | 市场机会 |
| tiktok_angle | TikTok MY 内容角度 |
| risk | 供应链/售后/合规风险 |
| recommendation | scale-test / test / watch / skip |

## 邮件发送策略

第一阶段建议创建 Gmail 草稿，确认格式稳定后再自动发送。

第二阶段自动发送：

- 每天 09:00 运行日报任务
- 生成 HTML 看板、CSV 明细、脚本表
- 邮件正文放结论和前 5-10 个重点商品
- 附件放完整看板和 CSV

