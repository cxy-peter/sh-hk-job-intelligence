#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from job_intel import (
    collect_all, dedupe_jobs, load_companies, load_seed_jobs, load_sources, load_state,
    mark_new, render_markdown, save_state, write_jobs_csv,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--companies", default="config/companies.yaml")
    parser.add_argument("--sources", default="config/sources.yaml")
    parser.add_argument("--seed-jobs", default="data/seed_jobs.csv")
    parser.add_argument("--state", default="data/state.json")
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--date")
    parser.add_argument("--seed-only", action="store_true", help="offline validation without network")
    args = parser.parse_args()

    today = args.date or dt.date.today().isoformat()
    companies = load_companies(args.companies)
    seed = load_seed_jobs(args.seed_jobs, companies)
    if args.seed_only:
        fetched, statuses = [], []
    else:
        fetched, statuses = collect_all(companies, load_sources(args.sources))
    jobs = dedupe_jobs(seed + fetched)
    state = load_state(args.state)
    mark_new(jobs, state, today)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    markdown = render_markdown(jobs, statuses, today)
    (out_dir / f"report_{today}.md").write_text(markdown, encoding="utf-8")
    (out_dir / "latest.md").write_text(markdown, encoding="utf-8")
    write_jobs_csv(out_dir / f"new_jobs_{today}.csv", [job for job in jobs if job.new_today], today)
    write_jobs_csv(out_dir / "latest_jobs.csv", jobs, today)
    save_state(args.state, state)
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
