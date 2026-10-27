import pytest
from app.core.security import (
    init_ed25519_keys,
    sign_data,
    verify_signature,
    generate_blind_index,
    get_password_hash,
    verify_password,
)
from app.services.credentials import issue_demo_credential, verify_credential_token

def test_ed25519_signing_and_verification():
    init_ed25519_keys()
    message = b'{"student_id": 101, "apaar": "9182-7364-5019"}'
    sig = sign_data(message)
    assert isinstance(sig, str)
    assert len(sig) > 20

    # Verification passes
    assert verify_signature(message, sig) is True

    # Tampering: change 1 character in message
    tampered_message = b'{"student_id": 102, "apaar": "9182-7364-5019"}'
    assert verify_signature(tampered_message, sig) is False

def test_keyed_hmac_blind_index():
    raw_id = "9182-7364-5019"
    idx1 = generate_blind_index(raw_id)
    idx2 = generate_blind_index("918273645019")  # Same numeric value
    assert idx1 == idx2
    assert len(idx1) == 64  # SHA256 hex length

def test_password_hashing():
    pw = "secret-pass-2026"
    pw_hash = get_password_hash(pw)
    assert verify_password(pw, pw_hash) is True
    assert verify_password("wrong-pass", pw_hash) is False

def test_credential_revocation_detection():
    student = {
        "id": 5,
        "name": "Sneha Deshmukh",
        "apaar_id": "6728-1920-3847",
        "dob": "2004-04-18",
        "institution_id": "AICTE-IN-101",
        "verification_status": "DEMO_VERIFIED",
    }
    cred = issue_demo_credential(student)

    # Clean active verification
    v_clean = verify_credential_token(cred["canonical_json"], cred["signature"], is_revoked=False)
    assert v_clean["is_valid"] is True
    assert v_clean["status"] == "VERIFIED"

    # Revoked verification
    v_rev = verify_credential_token(
        cred["canonical_json"],
        cred["signature"],
        is_revoked=True,
        revocation_reason="Duplicate registration detected.",
    )
    assert v_rev["is_valid"] is False
    assert v_rev["status"] == "REVOKED"
