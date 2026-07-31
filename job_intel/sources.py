"""Actual data-source adapters. Every adapter reports source health."""
from __future__ import annotations

import csv
import hashlib
import io
import re
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .classify import match_company
from .models import Company, Job, SourceStatus


HEADERS = {"User-Agent": "sh-hk-job-intelligence/2.0 (+personal research; low frequency)"}


RECRUITMENT_SPLIT = re.compile(
    r"(?:202\d届|20\d{2}|暑期|秋招|春招|校园|校招|招聘|实习|管培|应届|提前批|诚聘|职位)",
    re.I,
)


def _discover_company_name(title: str) -> str:
    """Best-effort company name extraction for official announcement titles."""
    cleaned = re.sub(r"^[【\[][^】\]]+[】\]]", "", title).strip()
    candidate = RECRUITMENT_SPLIT.split(cleaned, maxsplit=1)[0].strip(" -—丨|：:，,。")
    if len(candidate) < 3:
        candidate = cleaned[:40].strip(" -—丨|：:，,。")
    return candidate[:80]


def _discovered_company_id(name: str) -> str:
    digest = hashlib.sha1(name.casefold().encode("utf-8", errors="ignore")).hexdigest()[:12]
    return f"discovered_{digest}"


def _get(session: requests.Session, url: str, **kwargs) -> requests.Response:
    response = session.get(url, headers=HEADERS, timeout=25, **kwargs)
    response.raise_for_status()
    return response


def collect_greenhouse(source: dict, companies: list[Company], session: requests.Session) -> tuple[list[Job], SourceStatus]:
    board = source["board"]
    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
    try:
        rows = _get(session, url).json().get("jobs", [])
        company = next(c for c in companies if c.company_id == source["company_id"])
        jobs = []
        for row in rows:
            location = str((row.get("location") or {}).get("name", ""))
            jobs.append(Job(
                company_id=company.company_id, company=company.name, title=str(row.get("title", "")),
                location=location, url=str(row.get("absolute_url", "")), source=source["name"],
                source_tier=1, published=str(row.get("updated_at", ""))[:10],
                description=BeautifulSoup(str(row.get("content", "")), "html.parser").get_text(" ", strip=True),
                verification="官方ATS",
            ))
        return jobs, SourceStatus(source["name"], "ok", f"Greenhouse board={board}", len(jobs))
    except Exception as exc:
        return [], SourceStatus(source["name"], "error", f"{type(exc).__name__}: {exc}")


def collect_lever(source: dict, companies: list[Company], session: requests.Session) -> tuple[list[Job], SourceStatus]:
    site = source["site"]
    try:
        rows = _get(session, f"https://api.lever.co/v0/postings/{site}", params={"mode": "json"}).json()
        company = next(c for c in companies if c.company_id == source["company_id"])
        jobs = []
        for row in rows:
            categories = row.get("categories") or {}
            jobs.append(Job(
                company_id=company.company_id, company=company.name, title=str(row.get("text", "")),
                location=str(categories.get("location", "")), url=str(row.get("hostedUrl", "")),
                source=source["name"], source_tier=1, description=str(row.get("descriptionPlain", "")),
                verification="官方ATS",
            ))
        return jobs, SourceStatus(source["name"], "ok", f"Lever site={site}", len(jobs))
    except Exception as exc:
        return [], SourceStatus(source["name"], "error", f"{type(exc).__name__}: {exc}")


def collect_ashby(source: dict, companies: list[Company], session: requests.Session) -> tuple[list[Job], SourceStatus]:
    board = source["board"]
    try:
        payload = _get(session, f"https://api.ashbyhq.com/posting-api/job-board/{board}").json()
        company = next(c for c in companies if c.company_id == source["company_id"])
        jobs = []
        for row in payload.get("jobs", []) or []:
            jobs.append(Job(
                company_id=company.company_id, company=company.name, title=str(row.get("title", "")),
                location=str(row.get("location", "")), url=str(row.get("jobUrl", "")),
                source=source["name"], source_tier=1, description=str(row.get("descriptionPlain", "")),
                published=str(row.get("publishedAt", ""))[:10], verification="官方ATS",
            ))
        return jobs, SourceStatus(source["name"], "ok", f"Ashby board={board}", len(jobs))
    except Exception as exc:
        return [], SourceStatus(source["name"], "error", f"{type(exc).__name__}: {exc}")


def collect_generic_html(source: dict, companies: list[Company], session: requests.Session) -> tuple[list[Job], SourceStatus]:
    url = source["url"]
    try:
        response = _get(session, url)
        soup = BeautifulSoup(response.text, "html.parser")
        company = None
        if source.get("company_id"):
            company = next(c for c in companies if c.company_id == source["company_id"])
        jobs: list[Job] = []
        seen: set[str] = set()
        include = tuple(str(x).casefold() for x in source.get("include", []))
        exclude = tuple(str(x).casefold() for x in source.get("exclude", []))
        for anchor in soup.select("a[href]"):
            title = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True))
            href = urljoin(response.url, anchor.get("href", ""))
            if len(title) < 4 or href in seen:
                continue
            probe = f"{title} {href}".casefold()
            if include and not any(token in probe for token in include):
                continue
            if exclude and any(token in probe for token in exclude):
                continue
            matched = company or match_company(title, companies)
            if matched is None and source.get("allow_unmatched"):
                discovered_name = _discover_company_name(title)
                if len(discovered_name) < 3:
                    continue
                company_id = _discovered_company_id(discovered_name)
                company_name = discovered_name
            elif matched is not None:
                company_id = matched.company_id
                company_name = matched.name
            else:
                continue
            seen.add(href)
            jobs.append(Job(
                company_id=company_id, company=company_name, title=title,
                location=str(source.get("default_location", "")),
                url=href, source=source["name"], source_tier=int(source.get("tier", 1)),
                published=date.today().isoformat(), verification="官方页面待详情核验",
            ))
        status = "ok" if jobs else "partial"
        detail = f"HTTP {response.status_code}; extracted {len(jobs)} candidate links"
        return jobs, SourceStatus(source["name"], status, detail, len(jobs))
    except Exception as exc:
        return [], SourceStatus(source["name"], "error", f"{type(exc).__name__}: {exc}")


def collect_csv(source: dict, companies: list[Company], session: requests.Session) -> tuple[list[Job], SourceStatus]:
    try:
        response = _get(session, source["url"])
        rows = list(csv.DictReader(io.StringIO(response.text)))
        jobs: list[Job] = []
        for row in rows:
            text = " ".join(str(v or "") for v in row.values())
            company = match_company(text, companies)
            if not company:
                continue
            jobs.append(Job(
                company_id=company.company_id, company=company.name,
                title=str(row.get(source.get("title_field", "title"), "")),
                location=str(row.get(source.get("location_field", "city"), "")),
                deadline=str(row.get(source.get("deadline_field", "deadline"), "")),
                url=str(row.get(source.get("url_field", "url"), "")),
                source=source["name"], source_tier=int(source.get("tier", 3)),
                description=str(row.get(source.get("description_field", "job_description"), "")),
                published=str(row.get(source.get("published_field", "refresh_time"), "")),
                verification="聚合源，需回官方核验",
            ))
        return jobs, SourceStatus(source["name"], "ok", f"Read {len(rows)} CSV rows", len(jobs))
    except Exception as exc:
        return [], SourceStatus(source["name"], "error", f"{type(exc).__name__}: {exc}")


def collect_web_search(source: dict, companies: list[Company]) -> tuple[list[Job], SourceStatus]:
    if not source.get("enabled", True):
        return [], SourceStatus(source["name"], "disabled", "Disabled by config")
    try:
        from ddgs import DDGS
        jobs: list[Job] = []
        with DDGS() as ddgs:
            for query in source.get("queries", []):
                for row in ddgs.text(query, max_results=int(source.get("max_results", 10))):
                    title = str(row.get("title", ""))
                    body = str(row.get("body", ""))
                    url = str(row.get("href", ""))
                    company = match_company(f"{title} {body}", companies)
                    if company:
                        company_id, company_name = company.company_id, company.name
                    elif source.get("allow_unmatched"):
                        company_name = _discover_company_name(title)
                        if len(company_name) < 3:
                            continue
                        company_id = _discovered_company_id(company_name)
                    else:
                        continue
                    jobs.append(Job(
                        company_id=company_id, company=company_name, title=title,
                        location=str(source.get("default_location", "")),
                        url=url, source=source["name"], source_tier=int(source.get("tier", 3)),
                        description=body, verification="搜索线索，需回官方核验",
                    ))
        return jobs, SourceStatus(source["name"], "ok", "Public web search completed", len(jobs))
    except Exception as exc:
        return [], SourceStatus(source["name"], "blocked", f"{type(exc).__name__}: {exc}")



def collect_local_csv(source: dict, companies: list[Company]) -> tuple[list[Job], SourceStatus]:
    """Ingest a CSV exported by Codex/agent-browser skills such as shixiseng-job-csv."""
    path = Path(str(source.get("path", "")))
    if not path.exists():
        return [], SourceStatus(source["name"], "blocked", f"Waiting for local export: {path}")
    try:
        rows = list(csv.DictReader(path.open(encoding="utf-8-sig", newline="")))
        jobs: list[Job] = []
        for row in rows:
            text = " ".join(str(v or "") for v in row.values())
            company = match_company(text, companies)
            if company:
                company_id, company_name = company.company_id, company.name
            elif source.get("allow_unmatched"):
                company_name = str(row.get(source.get("company_field", "company"), "")).strip()
                if len(company_name) < 2:
                    continue
                company_id = _discovered_company_id(company_name)
            else:
                continue
            jobs.append(Job(
                company_id=company_id, company=company_name,
                title=str(row.get(source.get("title_field", "title"), "")),
                location=str(row.get(source.get("location_field", "city"), "")),
                deadline=str(row.get(source.get("deadline_field", "deadline"), "")),
                url=str(row.get(source.get("url_field", "url"), "")),
                source=source["name"], source_tier=int(source.get("tier", 3)),
                description=str(row.get(source.get("description_field", "job_description"), "")),
                published=str(row.get(source.get("published_field", "refresh_time"), "")),
                verification="外部Skill导出，需回官方核验",
            ))
        return jobs, SourceStatus(source["name"], "ok", f"Read {len(rows)} local CSV rows", len(jobs))
    except Exception as exc:
        return [], SourceStatus(source["name"], "error", f"{type(exc).__name__}: {exc}")


def collect_company_pool_html(
    source: dict, companies: list[Company], session: requests.Session
) -> tuple[list[Job], SourceStatus]:
    """Scan a bounded daily slice of the configured official career pages.

    A fixed core is checked every day; the rest is rotated across buckets so the
    company universe is genuinely covered without issuing 79 requests at once.
    """
    daily_ids = set(source.get("daily_company_ids", []))
    priorities = set(source.get("rotate_priorities", ["P0", "P1"]))
    buckets = max(1, int(source.get("rotation_buckets", 7)))
    bucket = date.today().toordinal() % buckets
    rotating = [
        c for c in companies
        if c.official_careers and c.priority in priorities and c.company_id not in daily_ids
        and int(hashlib.sha1(c.company_id.encode()).hexdigest(), 16) % buckets == bucket
    ]
    rotating = rotating[: max(0, int(source.get("max_rotating", 10)))]
    selected = [c for c in companies if c.company_id in daily_ids and c.official_careers] + rotating
    jobs: list[Job] = []
    ok = partial = failed = 0
    for company in selected:
        child = {
            "name": f"{source['name']}/{company.name}",
            "type": "generic_html",
            "company_id": company.company_id,
            "url": company.official_careers,
            "tier": int(source.get("tier", 1)),
            "include": source.get("include", ["job", "career", "招聘", "校园", "实习", "graduate", "analyst", "risk", "compliance", "product"]),
            "exclude": source.get("exclude", ["privacy", "cookie", "terms"]),
        }
        found, status = collect_generic_html(child, companies, session)
        jobs.extend(found)
        if status.status == "ok":
            ok += 1
        elif status.status == "partial":
            partial += 1
        else:
            failed += 1
    state = "ok" if selected and failed == 0 and partial == 0 else ("partial" if selected and (ok or partial) else "error")
    detail = f"Scanned {len(selected)} official pages: {ok} ok, {partial} empty/partial, {failed} failed; rotation bucket {bucket}/{buckets}"
    return jobs, SourceStatus(source["name"], state, detail, len(jobs))

def collect_source(source: dict, companies: list[Company], session: requests.Session):
    if source.get("enabled") is False:
        return [], SourceStatus(source.get("name", "unknown"), "disabled", "Disabled by config")
    kind = source.get("type")
    if kind == "greenhouse":
        return collect_greenhouse(source, companies, session)
    if kind == "lever":
        return collect_lever(source, companies, session)
    if kind == "ashby":
        return collect_ashby(source, companies, session)
    if kind == "generic_html":
        return collect_generic_html(source, companies, session)
    if kind == "csv":
        return collect_csv(source, companies, session)
    if kind == "local_csv":
        return collect_local_csv(source, companies)
    if kind == "company_pool_html":
        return collect_company_pool_html(source, companies, session)
    if kind == "web_search":
        return collect_web_search(source, companies)
    return [], SourceStatus(source.get("name", "unknown"), "error", f"Unknown source type: {kind}")
