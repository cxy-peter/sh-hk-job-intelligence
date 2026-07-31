"""Direct company-and-new-position report output."""
from __future__ import annotations

import csv
from pathlib import Path

from .models import Job, SourceStatus


FIELDS = [
    "发现日期", "公司", "职位", "地点", "批次", "面向届别", "职能方向", "截止日期",
    "匹配分", "是否今日新增", "来源", "来源级别", "原始链接", "核验状态",
]


def write_jobs_csv(path: str | Path, jobs: list[Job], today: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for job in sorted(jobs, key=lambda x: (-x.match_score, x.company, x.title)):
            writer.writerow({
                "发现日期": today,
                "公司": job.company,
                "职位": job.title,
                "地点": job.location,
                "批次": job.batch,
                "面向届别": job.cohort,
                "职能方向": job.function,
                "截止日期": job.deadline,
                "匹配分": job.match_score,
                "是否今日新增": "是" if job.new_today else "否",
                "来源": job.source,
                "来源级别": job.source_tier,
                "原始链接": job.url,
                "核验状态": job.verification,
            })


def render_markdown(jobs: list[Job], statuses: list[SourceStatus], today: str) -> str:
    new_jobs = [job for job in jobs if job.new_today]
    priority_new = [job for job in new_jobs if job.match_score >= 55]
    active = [job for job in jobs if job.match_score >= 35]
    out = [
        f"# 沪港秋招情报 · {today}",
        "",
        "## 今日结论",
    ]
    if priority_new:
        out.append(f"**发现 {len(priority_new)} 个高匹配新增岗位/招聘批次。**")
    elif new_jobs:
        out.append(f"发现 {len(new_jobs)} 个新增线索，但暂时没有达到高匹配阈值的岗位。")
    else:
        out.append("**今日未发现新增岗位，继续保留开放岗位表。**")

    out += [
        "",
        "## 公司与新增职位",
        "| 公司 | 新职位/批次 | 地点 | 批次 | 届别 | 方向 | 截止 | 匹配分 | 核验 | 来源 |",
        "|---|---|---|---|---|---|---|---:|---|---|",
    ]
    rows = sorted(new_jobs, key=lambda x: (-x.match_score, x.company, x.title))[:50]
    if not rows:
        out.append("| — | 今日无新增 | — | — | — | — | — | — | — | — |")
    for job in rows:
        title = job.title.replace("|", "/")
        title = f"[{title}]({job.url})" if job.url else title
        out.append(
            f"| {job.company} | {title} | {job.location or '待识别'} | {job.batch} | {job.cohort or '待识别'} | {job.function} | {job.deadline or '待核验'} | {job.match_score} | {job.verification} | {job.source} |"
        )

    out += [
        "",
        "## 当前开放/待核验岗位（按匹配分）",
        "| 公司 | 职位/批次 | 地点 | 方向 | 匹配分 | 状态 |",
        "|---|---|---|---|---:|---|",
    ]
    for job in sorted(active, key=lambda x: (-x.match_score, x.company, x.title))[:80]:
        title = job.title.replace("|", "/")
        title = f"[{title}]({job.url})" if job.url else title
        out.append(f"| {job.company} | {title} | {job.location or '待识别'} | {job.function} | {job.match_score} | {job.verification} |")

    discovered = [job for job in jobs if job.company_id.startswith("discovered_")]
    out += [
        "",
        "## 新发现公司（待纳入公司池）",
        "| 公司 | 触发岗位/公告 | 地点 | 来源 | 核验动作 |",
        "|---|---|---|---|---|",
    ]
    if not discovered:
        out.append("| — | 今日没有公司池外的新机构 | — | — | — |")
    for job in sorted(discovered, key=lambda x: (-x.match_score, x.company))[:30]:
        title = job.title.replace("|", "/")
        title = f"[{title}]({job.url})" if job.url else title
        out.append(f"| {job.company} | {title} | {job.location or '待识别'} | {job.source} | 核验公司性质、地点与官方招聘入口后加入 companies.yaml |")

    out += [
        "",
        "## 数据源健康",
        "| 数据源 | 状态 | 抓取数 | 详情 |",
        "|---|---|---:|---|",
    ]
    for status in statuses:
        out.append(f"| {status.source} | {status.status} | {status.jobs_found} | {status.detail.replace('|', '/')} |")

    out += [
        "",
        "## 筛选规则",
        "- 优先级：上海 > 香港 > 纽约 > 美国其他 > 北京；WLB优先于纯薪资。",
        "- 重点：跨境支付、清算/金融基础设施、支付风控、AML/KYC、合规、产品、数据分析、运营策略、AI Agent。",
        "- 排除或显著降权：量化、券商、公募基金、银行总行常规岗；高级职位不会伪装成应届岗位。",
        "- 微信公众号、小红书和聚合站只作为线索，最终必须回到企业官网或政府/国聘官方公告核验。",
    ]
    return "\n".join(out) + "\n"
