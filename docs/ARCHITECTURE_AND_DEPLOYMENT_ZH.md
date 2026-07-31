# 沪港秋招情报 v2：架构与部署

## 目标

每天直接回答两个问题：

1. 哪家公司出现了什么新职位/招聘批次？
2. 对用户的地区、赛道和岗位偏好而言，是否值得立即核验或投递？

## 执行链

```text
79家公司配置 + 公司池外发现
  -> 官方ATS/官网/上海国资委/搜索/本地Skill导出
  -> 公司匹配与新公司发现
  -> 地点/批次/届别/职能识别
  -> 用户特定评分
  -> state.json 去重
  -> 公司+新增岗位表 / 当前开放表 / 新发现公司 / 来源健康
```

## 为什么不是只列来源

- Greenhouse、Lever、Ashby 均调用实际 Job Board API。
- 官方 HTML 适配器解析真实链接并输出源状态。
- 公司池扫描器每天检查 11 个核心机构，并把其余 P0/P1 公司分为 7 个轮转桶，避免 79 个站点每天全量轰炸。
- 上海国资委与搜索结果支持 `allow_unmatched`：不在 `companies.yaml` 的新国企会保留为 `discovered_*`，而不是丢弃。
- 实习僧 Skill 的结果通过 `data/external/shixiseng_jobs.csv` 进入同一去重和评分链路。
- 微信、小红书等登录/交互型来源不会被伪装成普通 requests 已成功抓取；失败或等待导入会出现在来源健康表。

## 日常输出

- `reports/latest.md`
- `reports/latest_jobs.csv`
- `reports/new_jobs_YYYY-MM-DD.csv`
- `data/state.json`

没有新增时固定输出：

```text
今日未发现新增岗位，继续保留开放岗位表。
```

## 部署

```bash
pip install -r requirements.txt
pytest -q
python run_daily.py --seed-only --date 2026-07-31 --out-dir reports_seed
python run_daily.py --out-dir reports
```

GitHub Actions 每天 08:00（Asia/Shanghai）运行，无邮件递送。需要在仓库 Actions 设置中允许 workflow 写入内容，才能提交 `state.json` 与 `reports/`。

## Codex 浏览器补充任务

每天运行 `docs/DAILY_TASK_PROMPT.md` 中的 gap checks：

- P0 公司官网和官方 ATS；
- 上海国资委、国聘/24365；
- 公众号/小红书只作为线索；
- agent-browser 运行实习僧 Skill 后写入 `data/external/shixiseng_jobs.csv`；
- 所有线索回官方页面核验；
- 不把旧岗位重复称为“新增”。
