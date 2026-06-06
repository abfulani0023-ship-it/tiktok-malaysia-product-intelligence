# 云端日报部署说明

目标：让电脑可以关机，每天 09:00 自动生成并发送 Amazon US / SG / UK 到 TikTok Malaysia 的选品日报。

## 推荐方案

第一版使用 GitHub Actions：

- 不依赖你的电脑开机
- 每天 09:00 中国/马来西亚时间运行
- 自动生成 HTML 日报、CSV 明细、TikTok 脚本表
- 通过 Gmail SMTP 发到你的邮箱

## 需要你做的配置

### 1. 把项目放到 GitHub 仓库

当前目录还不是 Git 仓库。需要创建一个 GitHub 仓库并把项目推上去。

### 2. 开启 Gmail App Password

Gmail SMTP 需要 App Password，不建议使用你的 Gmail 登录密码。

步骤：

1. 打开 Google Account
2. 开启两步验证
3. 进入 App passwords
4. 创建一个用于 GitHub Actions 的 App Password
5. 保存生成的 16 位密码

### 3. 在 GitHub 仓库里配置 Secrets

进入：

```text
GitHub Repo -> Settings -> Secrets and variables -> Actions -> New repository secret
```

添加：

| Secret 名称 | 值 |
|---|---|
| `GMAIL_USER` | 你的 Gmail 发件邮箱 |
| `GMAIL_APP_PASSWORD` | Gmail App Password |
| `REPORT_RECIPIENT` | `richardlee19831228@gmail.com` |

### 4. 定时任务

工作流文件：

```text
.github/workflows/daily-product-report.yml
```

它已经设置为：

```text
每天 UTC 01:00
```

对应中国/马来西亚时间每天 09:00。

## 手动测试

进入 GitHub 仓库：

```text
Actions -> Daily Amazon to TikTok MY Product Report -> Run workflow
```

如果成功，你会收到日报邮件。

## 当前限制

当前云端版本会先使用项目里的 `data/amazon_products.csv` 作为数据源生成日报。

下一阶段需要接入真实 Amazon US / SG / UK 数据采集层，才能每天自动抓最新热门、上升品类、商品图、评论和关键词。

