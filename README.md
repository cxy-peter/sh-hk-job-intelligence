# Shanghai / Hong Kong Daily Job Intelligence v2

A daily job-intelligence pipeline built for the user's actual target profile rather than a generic job list.

## Output

Every run writes:

- `reports/latest.md` — a direct **company + new position** table.
- `reports/latest_jobs.csv` — all current leads, ranked by match score.
- `reports/new_jobs_YYYY-MM-DD.csv` — jobs first seen that day.
- `data/state.json` — persistent deduplication and first/last-seen dates.
- Source health — failed or blocked sources are visible; the system never silently treats a failed source as “no jobs.”
- A “新发现公司” section — Shanghai SASAC/search results outside the 79-company seed are retained for review instead of being discarded.

When there are no additions, the report says: **今日未发现新增岗位，继续保留开放岗位表。**

## User-specific ranking

The scorer encodes:

- Location: Shanghai > Hong Kong > New York > other US > Beijing.
- WLB is preferred over salary-only optimization.
- Strongly preferred: cross-border payments, clearing/financial infrastructure, payment risk, AML/KYC, compliance, product, data analytics, strategy & operations and AI Agent.
- Excluded or heavily penalized: quant, brokers, public funds and ordinary bank-head-office roles.
- Senior/manager roles are retained as market intelligence but penalized so they are not presented as graduate opportunities.

## Company universe

`config/companies.yaml` contains 79 companies and institutions, expanding the uploaded Excel into:

- Shanghai/Hong Kong payment and fintech.
- Global payments with Shanghai/Hong Kong offices.
- Clearing, settlement and RMB internationalization infrastructure.
- Shanghai municipal SOEs and financial/data infrastructure.
- Adjacent platform roles in compliance, risk, product and data.

## Sources that actually execute

The pipeline includes concrete adapters for:

- Greenhouse, Lever and Ashby official ATS APIs.
- Official HTML career pages.
- A bounded company-pool scanner: 11 core institutions daily, with P0/P1 pages rotated across seven buckets.
- Shanghai SASAC recruitment announcements, including companies not yet present in `companies.yaml`.
- Public web search for early-batch and social/public-account leads.
- Remote and local CSV ingestion for externally exported sources.

The `shixiseng-job-csv` skill is best run by Codex/agent-browser and exported to `data/external/shixiseng_jobs.csv`. The included `local_csv` adapter consumes it on the next daily run. The repository does not pretend that a normal `requests` call can bypass interactive/login-heavy sources such as Xiaohongshu or all WeChat pages.

## Run

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
pytest -q
python run_daily.py --seed-only --date 2026-07-31 --out-dir reports_seed
python run_daily.py --out-dir reports
```

## Daily automation

`.github/workflows/daily-jobs.yml` runs every day at 08:00 Asia/Shanghai, commits the updated table and state, and exposes the report in the GitHub Actions summary. There is no email delivery.

## Verification hierarchy

1. Company official careers/ATS.
2. Shanghai SASAC, 国聘, 24365 or other official government sources.
3. Reputable aggregators and public web search.
4. WeChat/Xiaohongshu/social posts as leads only.

A tier-3 lead must link back to an official page before application status is treated as confirmed.
