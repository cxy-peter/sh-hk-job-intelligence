"""Typed job intelligence records."""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field


@dataclass
class Company:
    company_id: str
    name: str
    english_name: str = ""
    aliases: list[str] = field(default_factory=list)
    category: str = ""
    subcategory: str = ""
    locations: list[str] = field(default_factory=list)
    ownership: str = ""
    priority: str = "P2"
    target_directions: list[str] = field(default_factory=list)
    official_careers: str = ""
    monitoring_channels: list[str] = field(default_factory=list)
    original_note: str = ""


@dataclass
class Job:
    company_id: str
    company: str
    title: str
    location: str = ""
    batch: str = "待识别"
    cohort: str = ""
    function: str = ""
    deadline: str = ""
    url: str = ""
    source: str = ""
    source_tier: int = 3
    published: str = ""
    description: str = ""
    verification: str = "待核验"
    match_score: int = 0
    new_today: bool = False
    job_id: str = ""

    def finalize_id(self) -> None:
        if self.job_id:
            return
        canonical = "|".join(
            [self.company_id, self.title.strip().casefold(), self.location.strip().casefold(), self.url.strip()]
        )
        self.job_id = hashlib.sha256(canonical.encode("utf-8", errors="ignore")).hexdigest()[:20]

    def to_dict(self) -> dict:
        self.finalize_id()
        return asdict(self)


@dataclass
class SourceStatus:
    source: str
    status: str  # ok | partial | blocked | error | disabled
    detail: str
    jobs_found: int = 0
