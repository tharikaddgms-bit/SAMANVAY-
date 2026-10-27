import pytest
from app.core.normalization import normalize_name, normalize_dob, validate_apaar_format

def test_name_normalization_whitespace():
    res = normalize_name("   arun    kumar   ")
    assert res["normalized"] == "ARUN KUMAR"
    assert not res["is_empty"]

def test_name_normalization_honorifics():
    res = normalize_name("Shri Rajesh Sharma")
    assert res["normalized"] == "RAJESH SHARMA"
    assert "HONORIFIC_STRIPPED" in res["changes_applied"]

def test_name_normalization_punctuation():
    res = normalize_name("Md. Rehan-Khan,")
    assert res["normalized"] == "MD REHAN KHAN"
    assert "PUNCTUATION_REMOVED" in res["changes_applied"]

def test_apaar_format_valid():
    res = validate_apaar_format("9182-7364-5019")
    assert res["is_valid"] is True
    assert res["clean_id"] == "918273645019"
    assert res["formatted"] == "9182-7364-5019"

def test_apaar_format_invalid_length():
    res = validate_apaar_format("8271-9304")  # 8 digits
    assert res["is_valid"] is False
    assert "Expected exactly 12 digits" in res["error_reason"]

def test_apaar_format_invalid_characters():
    res = validate_apaar_format("9823-ABCD-4019")
    assert res["is_valid"] is False
    assert "non-numeric" in res["error_reason"]

def test_dob_normalization_formats():
    res1 = normalize_dob("14/06/2004")
    assert res1["is_valid"] is True
    assert res1["canonical"] == "2004-06-14"

    res2 = normalize_dob("2004-06-14")
    assert res2["is_valid"] is True
    assert res2["canonical"] == "2004-06-14"
