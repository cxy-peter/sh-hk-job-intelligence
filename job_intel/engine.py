"""Daily job intelligence orchestration helpers."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import requests
import yaml

from .classify import enrich_job
from .models import Company, Job, SourceStatus
from .sources import collect_source


def load_companies(path: str | Path) -> list[Company]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []
    return [Company(**row) for row in raw]


def load_sources(path: str | Path) -> list[dict]:
    return list(yaml.safe_load(Path(path).read_text(encoding="utf-8")) or [])


def load_seed_jobs(path: str | Path, companies: list[Company]) -> list[Job]:
    target = Path(path)
    if not target.exists():
        return []
    by_id = {c.company_id: c for c in companies}
    jobs = []
    with target.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            job = Job(
                company_id=row["company_id"], company=row["company"], title=row["title"],
                location=row.get("location", ""), batch=row.get("batch", "待识别"),
                cohort=row.get("cohort", ""), function=row.get("function", ""),
                deadline=row.get("deadline", ""), url=row.get("url", ""),
                source=row.get("source", "seed"), source_tier=int(row.get("source_tier", 2)),
                published=row.get("published", ""), description=row.get("description", ""),
                verification=row.get("verification", "待核验"),
            )
            company = by_id.get(job.company_id)
            if company:
                jobs.append(enrich_job(job, company))
    return jobs


def collect_all(companies: list[Company], sources: list[dict]) -> tuple[list[Job], list[SourceStatus]]:
    session = requests.Session()
    jobs: list[Job] = []
    statuses: list[SourceStatus] = []
    by_id = {c.company_id: c for c in companies}
    for source in sources:
        found, status = collect_source(source, companies, session)
        statuses.append(status)
        for job in found:
            company = by_id.get(job.company_id)
            if company is None and job.company_id.startswith("discovered_"):
                company = Company(
                    company_id=job.company_id, name=job.company,
                    category="新发现/待归类", subcategory="自动发现",
                    locations=[job.location] if job.location else [],
                    ownership="待核验", priority="P1",
                    target_directions=["风控策略", "合规", "产品", "数据分析"],
                    monitoring_channels=[job.source],
                )
            if company:
                jobs.append(enrich_job(job, company))
    return dedupe_jobs(jobs), statuses


def dedupe_jobs(jobs: list[Job]) -> list[Job]:
    best: dict[str, Job] = {}
    for job in jobs:
        job.finalize_id()
        current = best.get(job.job_id)
        if current is None or (job.source_tier, -job.match_score) < (current.source_tier, -current.match_score):
            best[job.job_id] = job
    return list(best.values())


def load_state(path: str | Path) -> dict:
    target = Path(path)
    if not target.exists():
        return {"seen": {}}
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"seen": {}}


def mark_new(jobs: list[Job], state: dict, today: str) -> list[Job]:
    seen = state.setdefault("seen", {})
    for job in jobs:
        job.finalize_id()
        job.new_today = job.job_id not in seen
        record = seen.setdefault(job.job_id, {})
        record.setdefault("first_seen", today)
        record.update({"last_seen": today, "company": job.company, "title": job.title, "url": job.url})
    return jobs


def save_state(path: str | Path, state: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
