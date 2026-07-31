from job_intel.models import Company
from job_intel.sources import collect_generic_html


class Response:
    status_code = 200
    url = "https://example.com/careers"
    text = '<a href="/job/risk-analyst">2027 Graduate Risk Analyst - Shanghai</a><a href="/privacy">Privacy</a>'
    def raise_for_status(self):
        return None


class Session:
    def get(self, *args, **kwargs):
        return Response()


def test_generic_html_is_actual_extraction_not_placeholder():
    company = Company(company_id="c", name="TestPay", english_name="TestPay", priority="P0")
    jobs, status = collect_generic_html(
        {"name": "official", "type": "generic_html", "company_id": "c", "url": "https://example.com/careers", "include": ["/job/"], "tier": 1},
        [company], Session(),
    )
    assert status.status == "ok"
    assert len(jobs) == 1
    assert jobs[0].title.startswith("2027 Graduate Risk Analyst")
    assert jobs[0].url == "https://example.com/job/risk-analyst"


def test_generic_html_retains_company_outside_seed_pool():
    class UnmatchedResponse(Response):
        text = '<a href="/notice/new">上海新发现集团2027届校园招聘启动</a>'

    class UnmatchedSession(Session):
        def get(self, *args, **kwargs):
            return UnmatchedResponse()

    jobs, status = collect_generic_html(
        {
            "name": "上海国资委", "type": "generic_html",
            "url": "https://example.com/careers", "include": ["招聘"],
            "tier": 1, "allow_unmatched": True, "default_location": "上海",
        },
        [], UnmatchedSession(),
    )
    assert status.status == "ok"
    assert jobs[0].company == "上海新发现集团"
    assert jobs[0].company_id.startswith("discovered_")
    assert jobs[0].location == "上海"
