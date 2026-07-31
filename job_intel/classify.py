"""Job normalization, company matching and user-specific scoring."""
from __future__ import annotations

import re

from .models import Company, Job


LOCATION_TERMS = {
    "上海": ("上海", "shanghai"),
    "香港": ("香港", "hong kong", "hong kong sar"),
    "纽约": ("纽约", "new york", "nyc"),
    "北京": ("北京", "beijing"),
    "深圳": ("深圳", "shenzhen"),
}

FUNCTION_TERMS = {
    "风控策略": ("风控策略", "risk strategy", "fraud strategy", "transaction risk", "risk analytics"),
    "合规/AML": ("合规", "aml", "kyc", "edd", "sanction", "transaction monitoring", "financial crime"),
    "支付产品": ("支付产品", "payment product", "payments product", "cross-border payment", "跨境支付"),
    "数据分析": ("数据分析", "data analyst", "analytics", "business intelligence", "bi analyst"),
    "产品经理": ("产品经理", "product manager", "product analyst"),
    "运营策略": ("运营策略", "strategy & operations", "strategy and operations", "operations analyst"),
    "金融科技": ("金融科技", "fintech", "digital finance", "数字金融"),
    "清算/基础设施": ("清算", "clearing", "settlement", "financial infrastructure", "金融基础设施"),
    "AI/Agent": ("ai agent", "agent", "大模型", "llm", "machine learning"),
}

BATCH_TERMS = [
    ("提前批", ("提前批", "early batch", "early careers", "early bird", "早鸟")),
    ("秋招", ("秋招", "autumn recruitment", "graduate programme", "graduate program")),
    ("暑期实习/留用", ("暑期实习", "summer internship", "summer intern", "留用")),
    ("春招", ("春招", "spring recruitment")),
    ("日常招聘", ("full time", "experienced hire", "社会招聘")),
]

EXCLUDE_TERMS = (
    "量化", "quantitative researcher", "quant trader", "证券经纪", "brokerage sales",
    "公募基金", "基金销售", "柜员", "客户经理（零售）", "relationship manager retail",
)


def _contains(text: str, terms) -> bool:
    lowered = text.casefold()
    return any(term.casefold() in lowered for term in terms)


def match_company(text: str, companies: list[Company]) -> Company | None:
    lowered = text.casefold()
    best = None
    best_len = 0
    for company in companies:
        names = [company.name, company.english_name, *company.aliases]
        for name in names:
            token = name.strip()
            if not token:
                continue
            folded = token.casefold()
            # Very short ASCII aliases (e.g. KN/OSL/SFC) must match a token
            # boundary; otherwise normal prose produces false company hits.
            if token.isascii() and len(token) <= 3:
                matched = re.search(rf"(?<![a-z0-9]){re.escape(folded)}(?![a-z0-9])", lowered) is not None
            else:
                matched = len(token) >= 2 and folded in lowered
            if matched and len(token) > best_len:
                best, best_len = company, len(token)
    return best


def infer_location(text: str) -> str:
    found = [name for name, terms in LOCATION_TERMS.items() if _contains(text, terms)]
    return "/".join(found)


def infer_function(text: str) -> str:
    found = [name for name, terms in FUNCTION_TERMS.items() if _contains(text, terms)]
    return "/".join(found[:3]) or "其他"


def infer_batch(text: str) -> str:
    for name, terms in BATCH_TERMS:
        if _contains(text, terms):
            return name
    return "待识别"


def infer_cohort(text: str) -> str:
    years = sorted(set(re.findall(r"20(?:2[5-9]|3\d)届", text)))
    if years:
        return "/".join(years)
    match = re.search(r"(20(?:2[5-9]|3\d))\s*(?:graduate|graduates|campus)", text, re.I)
    return f"{match.group(1)}届" if match else ""


def score_job(job: Job, company: Company, text: str) -> int:
    score = {"P0": 35, "P1": 25, "P2": 15, "P3": 5}.get(company.priority, 10)
    enriched_text = " ".join([text, job.function, job.batch, job.cohort, " ".join(company.target_directions)])
    location = job.location or infer_location(enriched_text)
    if "上海" in location:
        score += 25
    elif "香港" in location:
        score += 20
    elif "纽约" in location:
        score += 8
    elif "北京" in location:
        score += 2
    directions = job.function or infer_function(enriched_text)
    if any(term in directions for term in ("风控策略", "合规/AML", "支付产品", "清算/基础设施")):
        score += 22
    if any(term in directions for term in ("数据分析", "产品经理", "运营策略", "AI/Agent")):
        score += 12
    batch = job.batch or infer_batch(enriched_text)
    if batch == "提前批":
        score += 12
    elif batch in {"秋招", "暑期实习/留用"}:
        score += 8
    if job.source_tier == 1:
        score += 8
    elif job.source_tier == 2:
        score += 4
    if _contains(enriched_text, EXCLUDE_TERMS):
        score -= 45

    title_lower = job.title.casefold()
    if any(term in title_lower for term in ("senior", "lead", "principal", "director", "head of", "负责人", "高级经理")):
        score -= 45
    elif "manager" in title_lower and "product manager" not in title_lower and "管培" not in job.title:
        score -= 25
    if any(term in enriched_text.casefold() for term in ("5+ years", "8+ years", "10+ years", "五年以上", "八年以上")):
        score -= 35
    return max(0, min(100, score))


def enrich_job(job: Job, company: Company) -> Job:
    text = " ".join([job.title, job.location, job.description])
    job.location = job.location or infer_location(text)
    job.function = job.function or infer_function(text)
    job.batch = job.batch if job.batch != "待识别" else infer_batch(text)
    job.cohort = job.cohort or infer_cohort(text)
    job.match_score = score_job(job, company, text)
    job.finalize_id()
    return job
