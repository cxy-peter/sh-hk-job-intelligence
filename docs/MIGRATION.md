# Deployment checklist

1. Create a new GitHub repository or place this package in the existing Codex project.
2. Copy `沪港秋招公司池与每日岗位表.xlsx` to your working folder as the human-facing tracker; runtime truth remains `config/companies.yaml` + `data/state.json`.
3. Run `pytest -q` and the seed-only smoke test.
4. Enable GitHub Actions write permission.
5. Trigger `daily-shanghai-hongkong-job-intelligence` manually once.
6. Review source health. A blocked source is not equivalent to zero jobs.
7. When Codex/agent-browser exports Shixiseng results, save them to `data/external/shixiseng_jobs.csv` using the fields documented by the skill.
8. Review `新发现公司（待纳入公司池）`; after validation, add worthwhile institutions to `config/companies.yaml` with an official careers URL and priority.
