from job_intel.engine import mark_new
from job_intel.models import Job, SourceStatus
from job_intel.report import render_markdown


def test_state_marks_only_unseen_jobs_new():
    first = Job("a", "A", "Risk Analyst", url="https://example/a")
    first.finalize_id()
    state = {"seen": {first.job_id: {"first_seen": "2026-07-30"}}}
    second = Job("b", "B", "Product Analyst", url="https://example/b")
    mark_new([first, second], state, "2026-07-31")
    assert not first.new_today
    assert second.new_today


def test_report_has_explicit_no_new_message_and_direct_table():
    job = Job("a", "A", "Risk Analyst", location="上海", match_score=80, new_today=False)
    text = render_markdown([job], [SourceStatus("source", "ok", "done", 1)], "2026-07-31")
    assert "今日未发现新增岗位，继续保留开放岗位表" in text
    assert "公司与新增职位" in text
