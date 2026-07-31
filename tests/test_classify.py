from job_intel.classify import enrich_job, infer_batch, infer_cohort, infer_function, infer_location
from job_intel.models import Company, Job


def company(priority="P0"):
    return Company(
        company_id="airwallex", name="Airwallex空中云汇", english_name="Airwallex",
        priority=priority, locations=["上海", "香港"], target_directions=["支付风控"],
    )


def test_inference_for_early_payment_risk_role():
    text = "Airwallex 2027届秋招提前批 支付风控策略分析师 上海"
    assert infer_location(text) == "上海"
    assert infer_batch(text) == "提前批"
    assert infer_cohort(text) == "2027届"
    assert "风控策略" in infer_function(text)


def test_user_specific_score_prioritizes_shanghai_payment_risk():
    job = Job("airwallex", "Airwallex空中云汇", "2027届支付风控策略分析师", location="上海", batch="提前批", source_tier=1)
    enriched = enrich_job(job, company())
    assert enriched.match_score >= 80


def test_senior_role_is_penalized():
    junior = enrich_job(Job("airwallex", "Airwallex空中云汇", "Risk Analyst", location="香港", source_tier=1), company())
    senior = enrich_job(Job("airwallex", "Airwallex空中云汇", "Senior Risk Manager 8+ years", location="香港", source_tier=1), company())
    assert senior.match_score < junior.match_score


def test_senior_role_falls_below_high_match_threshold():
    senior = enrich_job(
        Job("airwallex", "Airwallex空中云汇", "Transaction Monitoring Senior Analyst", location="上海", function="合规/AML", source_tier=1),
        company(),
    )
    assert senior.match_score < 55
