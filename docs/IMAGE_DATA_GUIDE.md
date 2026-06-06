# 商品图片接入说明

日报支持直接显示商品图片。

## 图片字段

在 `data/amazon_products.csv` 里填写：

```text
image_url
```

只要 `image_url` 有值，日报会在商品卡片左侧显示图片；如果为空，就显示 “IMAGE / 待采集商品图” 占位。

## 推荐图片来源

优先级：

1. Amazon 商品页主图 URL
2. Amazon Product Advertising API 返回的图片
3. 合规第三方商品数据 API 返回的图片
4. 自己供应链或货盘提供的商品图

## 注意

- 不要手工盗用有明显版权风险的品牌图做投放素材。
- 日报内部分析可以引用商品图帮助判断，但真正做 TikTok 素材时，优先使用供应链授权图、自己实拍图或 AI 重制图。
- 图片 URL 建议使用 `https://...jpg` 或 `https://...png` 的直接图片链接。

