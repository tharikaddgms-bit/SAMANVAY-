import pytest
from app.services.fuzzy_matching import (
    calculate_name_similarity,
    check_dob_transposition,
    compute_duplicate_candidate_score,
)

def test_name_similarity_spelling_variation():
    res = calculate_name_similarity("Arun Kumar", "Arun Kumaar")
    assert res["score"] >= 90.0
    assert not res["is_exact"]

def test_name_similarity_phonetic():
    res = calculate_name_similarity("Pooja Sharma", "Puja Sharma")
    assert res["score"] >= 85.0

def test_dob_transposition():
    is_transp, reason = check_dob_transposition("2004-03-08", "2004-08-03")
    assert is_transp is True
    assert reason == "DAY_MONTH_TRANSPOSITION"

def test_duplicate_candidate_scoring():
    rec_a = {
        "id": 1,
        "name": "Arun Kumar",
        "dob": "2003-05-12",
        "guardian_name": "Satish Kumar",
        "apaar_id": "1928-3746-5091",
        "institution_id": "AICTE-IN-101",
    }
    rec_b = {
        "id": 2,
        "name": "Arun Kumaar",
        "dob": "2003-05-12",
        "guardian_name": "Satish Kumar",
        "apaar_id": "1928-3746-5091",
        "institution_id": "AICTE-MH-204",
    }
    cand = compute_duplicate_candidate_score(rec_a, rec_b)
    assert cand is not None
    assert cand["composite_score"] >= 88.0
    assert cand["is_cross_institution"] is True
