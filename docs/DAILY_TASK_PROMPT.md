# Codex daily-task specification

Run the project and then perform the following browser-assisted gap checks before finalizing `reports/latest.md`:

1. Search each P0 company for 2027 graduate, autumn recruitment, early batch, summer-to-return and management trainee notices.
2. Search official company careers first; then Shanghai SASAC, 国聘/24365 and university career centers.
3. Search indexed WeChat and Xiaohongshu results only as leads. Record a social item as `待核验` until an official page is found.
4. Run/import `s0meb0dy3/shixiseng-job-csv` for keywords: 跨境支付, 支付风控, 反洗钱, KYC, 合规, 风控策略, 数据分析, 产品经理, 清算, 金融科技. Limit to Shanghai or Hong Kong.
5. Compare normalized job IDs against `data/state.json`; do not call an old unchanged job “new.”
6. Display company and new role directly. Include location, batch, cohort, deadline, match score, original URL and verification status.
7. If no new role is found, write exactly: `今日未发现新增岗位，继续保留开放岗位表。`
8. Do not send email. Persist the Markdown/CSV outputs and source-health failures.
