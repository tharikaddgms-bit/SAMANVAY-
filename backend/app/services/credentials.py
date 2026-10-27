import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from app.core.config import AICTE_INSTITUTION_CODE, AICTE_INSTITUTION_NAME
from app.core.security import sign_data, verify_signature, get_public_key_pem
from app.core.normalization import validate_apaar_format

def mask_apaar(raw_id: str) -> str:
    """Masks an APAAR ID to protect student privacy: e.g., 'XXXXXXXX-1234'."""
    clean = validate_apaar_format(raw_id)["clean_id"]
    if len(clean) >= 4:
        return f"XXXX-XXXX-{clean[-4:]}"
    return "XXXX-XXXX-XXXX"

def create_canonical_claims(
    credential_id: str,
    student_id: int,
    student_name: str,
    apaar_masked: str,
    dob: str,
    institution_id: str,
    institution_name: str,
    verification_status: str,
    issued_at: str,
    expires_at: str,
) -> Dict[str, Any]:
    """Generates canonical ordered dictionary for deterministic signing."""
    return {
        "apaar_masked": apaar_masked,
        "credential_id": credential_id,
        "dob_year": dob.split("-")[0] if "-" in dob else dob,
        "expires_at": expires_at,
        "institution_id": institution_id,
        "institution_name": institution_name,
        "is_demo": True,
        "issued_at": issued_at,
        "student_id": student_id,
        "student_name": student_name,
        "verification_status": verification_status,
    }

def issue_demo_credential(
    student: Dict[str, Any],
    validity_days: int = 365,
) -> Dict[str, Any]:
    """
    Issues an Ed25519-signed demonstration credential for an AICTE student record.
    Preserves privacy with masked APAAR and selective disclosure.
    """
    cred_id = f"CRED-DEMO-{uuid.uuid4().hex[:12].upper()}"
    now = datetime.now(timezone.utc)
    issued_at = now.isoformat()
    expires_at = (now + timedelta(days=validity_days)).isoformat()

    apaar_masked = mask_apaar(student.get("apaar_id", ""))

    claims = create_canonical_claims(
        credential_id=cred_id,
        student_id=student.get("id", 0),
        student_name=student.get("name", ""),
        apaar_masked=apaar_masked,
        dob=student.get("dob", ""),
        institution_id=student.get("institution_id", AICTE_INSTITUTION_CODE),
        institution_name=AICTE_INSTITUTION_NAME,
        verification_status=student.get("verification_status", "DEMO_VERIFIED"),
        issued_at=issued_at,
        expires_at=expires_at,
    )

    # Deterministic JSON bytes (sorted keys, no spaces)
    canonical_bytes = json.dumps(claims, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = sign_data(canonical_bytes)

    # Minimal payload for QR code: reference + signature (no private secrets or full PII!)
    qr_payload = {
        "v": 1,
        "type": "SAMANVAY_CREDENTIAL",
        "cid": cred_id,
        "inst": claims["institution_id"],
        "sig": signature,
        "verify_path": f"/verify?cid={cred_id}",
    }

    return {
        "credential_id": cred_id,
        "student_id": student.get("id"),
        "claims": claims,
        "canonical_json": canonical_bytes.decode("utf-8"),
        "signature": signature,
        "qr_payload_json": json.dumps(qr_payload, separators=(",", ":")),
        "issued_at": issued_at,
        "expires_at": expires_at,
        "is_revoked": False,
        "revocation_reason": None,
    }

def verify_credential_token(
    canonical_json: str,
    signature: str,
    is_revoked: bool = False,
    revocation_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Cryptographically verifies an Ed25519 demonstration credential
    and checks current revocation registry status.
    """
    data_bytes = canonical_json.encode("utf-8")
    sig_valid = verify_signature(data_bytes, signature)

    if not sig_valid:
        return {
            "is_valid": False,
            "status": "SIGNATURE_INVALID",
            "message": "Cryptographic signature mismatch! The credential data may have been altered.",
            "tampered": True,
        }

    try:
        claims = json.loads(canonical_json)
    except Exception:
        return {
            "is_valid": False,
            "status": "MALFORMED_CLAIMS",
            "message": "Credential claims JSON is malformed.",
        }

    # Check expiration
    expires_at_str = claims.get("expires_at")
    if expires_at_str:
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > expires_at:
            return {
                "is_valid": False,
                "status": "EXPIRED",
                "message": f"Credential expired on {expires_at_str}.",
                "claims": claims,
            }

    # Check revocation
    if is_revoked:
        return {
            "is_valid": False,
            "status": "REVOKED",
            "message": f"Credential was revoked by issuing institution. Reason: {revocation_reason or 'Not specified'}.",
            "claims": claims,
            "is_revoked": True,
            "revocation_reason": revocation_reason,
        }

    return {
        "is_valid": True,
        "status": "VERIFIED",
        "message": "Cryptographic Ed25519 signature is authentic and credential is in good standing.",
        "claims": claims,
        "public_key_pem": get_public_key_pem(),
        "is_revoked": False,
    }
