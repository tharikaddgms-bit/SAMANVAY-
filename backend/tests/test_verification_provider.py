import pytest
from app.services.verification_provider import (
    DemoProvider,
    OfficialProvider,
    VerificationStatus,
)

def test_demo_provider_boundaries():
    provider = DemoProvider(
        synthetic_cohort={
            "918273645019": {"name": "Aarav Sharma", "dob": "2004-06-14"}
        }
    )

    # 1. Matching synthetic record yields DEMO_VERIFIED
    res_match = provider.verify("9182-7364-5019", "Aarav Sharma", "2004-06-14")
    assert res_match["status"] == VerificationStatus.DEMO_VERIFIED
    assert res_match["status"] != VerificationStatus.OFFICIALLY_VERIFIED

    # 2. Valid format but not in synthetic cohort yields FORMAT_VALID
    res_unknown = provider.verify("1234-5678-9012", "Unknown Student", "2004-01-01")
    assert res_unknown["status"] == VerificationStatus.FORMAT_VALID
    assert res_unknown["status"] != VerificationStatus.OFFICIALLY_VERIFIED

    # 3. Malformed ID yields UNVERIFIED
    res_malformed = provider.verify("1234-INVALID", "Bad Student", "2004-01-01")
    assert res_malformed["status"] == VerificationStatus.UNVERIFIED

def test_official_provider_disabled_without_keys():
    official = OfficialProvider()
    assert official.is_configured is False
    with pytest.raises(RuntimeError) as exc_info:
        official.verify("9182-7364-5019", "Aarav Sharma", "2004-06-14")
    assert "OfficialProvider is disabled" in str(exc_info.value)
