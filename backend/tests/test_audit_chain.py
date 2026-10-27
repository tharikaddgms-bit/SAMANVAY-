import pytest
from app.services.audit_ledger import (
    GENESIS_HASH,
    create_audit_entry_payload,
    verify_audit_chain,
)

def test_audit_hash_chain_integrity():
    # Build a 3-block chain
    prev = GENESIS_HASH
    blocks = []

    for i in range(3):
        payload = create_audit_entry_payload(
            previous_hash=prev,
            actor_id="admin",
            actor_role="INSTITUTION_ADMIN",
            action_type=f"TEST_ACTION_{i}",
            record_id=str(i),
            details={"step": i},
            custom_timestamp=f"2026-10-26T10:0{i}:00Z",
        )
        payload["id"] = i + 1
        blocks.append(payload)
        prev = payload["entry_hash"]

    # Clean chain verification
    res = verify_audit_chain(blocks)
    assert res["is_valid"] is True
    assert res["chain_status"] == "VERIFIED_SECURE"

    # Tampering test: modify details of block 1
    blocks[1]["details_json"] = '{"step":999}'
    res_tampered = verify_audit_chain(blocks)
    assert res_tampered["is_valid"] is False
    assert res_tampered["tampered_entry_id"] == 2
