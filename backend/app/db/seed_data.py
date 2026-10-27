import json
from datetime import datetime, timezone, timedelta

from app.core.config import AICTE_INSTITUTION_CODE, AICTE_INSTITUTION_NAME
from app.core.normalization import normalize_name, normalize_dob, validate_apaar_format
from app.core.security import get_password_hash, generate_blind_index
from app.services.credentials import issue_demo_credential
from app.services.audit_ledger import GENESIS_HASH, create_audit_entry_payload
from app.db.database import get_db

SYNTHETIC_STUDENTS = [
    {
        "name": "Aarav Sharma",
        "dob": "2004-06-14",
        "guardian_name": "Rajesh Sharma",
        "apaar_id": "9182-7364-5019",
        "institution_id": AICTE_INSTITUTION_CODE,
        "institution_name": AICTE_INSTITUTION_NAME,
        "program": "B.Tech Computer Science & Engineering",
        "verification_status": "DEMO_VERIFIED",
        "review_status": "APPROVED",
    },
    {
        "name": "Puja Sharma",
        "dob": "2003-11-22",
        "guardian_name": "Vinod Sharma",
        "apaar_id": "8391-0294-7162",
        "institution_id": AICTE_INSTITUTION_CODE,
        "institution_name": AICTE_INSTITUTION_NAME,
        "program": "B.Tech Electronics & Communication",
        "verification_status": "FORMAT_VALID",
        "review_status": "REQUIRES_CORRECTION",
        "discrepancy": {
            "field": "name",
            "existing": "Puja Sharma",
            "proposed": "Pooja Sharma",
            "reason": "Spelling variation detected (Phonetic u/oo variation)",
            "score": 88.5,
            "severity": "MEDIUM",
        },
    },
    {
        "name": "Arun Kumar",
        "dob": "2003-05-12",
        "guardian_name": "Satish Kumar",
        "apaar_id": "1928-3746-5091",
        "institution_id": AICTE_INSTITUTION_CODE,
        "institution_name": AICTE_INSTITUTION_NAME,
        "program": "B.Tech Information Technology",
        "verification_status": "DEMO_VERIFIED",
        "review_status": "APPROVED",
    },
    {
        "name": "Arun Kumaar",
        "dob": "2003-05-12",
        "guardian_name": "Satish Kumar",
        "apaar_id": "1928-3746-5091",
        "institution_id": "AICTE-MH-204",
        "institution_name": "College of Engineering Pune (Tech Autonomous)",
        "program": "B.Tech Computer Engineering",
        "verification_status": "DEMO_VERIFIED",
        "review_status": "PENDING_REVIEW",
        "is_duplicate_with_index": 2,  # Arun Kumar
    },
    {
        "name": "Rohan Verma",
        "dob": "2004-03-08",
        "guardian_name": "Deepak Verma",
        "apaar_id": "5647-3829-1029",
        "institution_id": AICTE_INSTITUTION_CODE,
        "institution_name": AICTE_INSTITUTION_NAME,
        "program": "B.Tech Mechanical Engineering",
        "verification_status": "FORMAT_VALID",
        "review_status": "REQUIRES_CORRECTION",
        "discrepancy": {
            "field": "dob",
            "existing": "2004-03-08",
            "proposed": "2004-08-03",
            "reason": "Date of Birth day/month transposition mismatch (08-03 vs 03-08)",
            "score": 85.0,
            "severity": "HIGH",
        },
    },
    {
        "name": "Sanya Kapoor",
        "dob": "2004-01-19",
        "guardian_name": "Vikram Kapoor",
        "apaar_id": "4738-2910-4820",
        "institution_id": AICTE_INSTITUTION_CODE,
        "institution_name": AICTE_INSTITUTION_NAME,
        "program": "B.Tech Artificial Intelligence & Data Science",
        "verification_status": "DEMO_VERIFIED",
        "review_status": "CORRECTED",
        "discrepancy": {
            "field": "guardian_name",
            "existing": "Late Shri Vikram Kapoor",
            "proposed": "Vikram Kapoor",
            "reason": "Honorific 'Late Shri' removed during institutional reconciliation",
            "score": 92.0,
            "severity": "LOW",
            "resolved": True,
        },
    },
    {
        "name": "Md. Rehan",
        "dob": "2003-09-15",
        "guardian_name": "Abdul Rehan",
        "apaar_id": "9283-7461-5038",
        "institution_id": AICTE_INSTITUTION_CODE,
        "institution_name": AICTE_INSTITUTION_NAME,
        "program": "B.Tech Civil Engineering",
        "verification_status": "FORMAT_VALID",
        "review_status": "REQUIRES_CORRECTION",
        "discrepancy": {
            "field": "name",
            "existing": "Md. Rehan",
            "proposed": "Mohammad Rehan",
            "reason": "Abbreviation 'Md.' expanded in official identity document",
            "score": 78.0,
            "severity": "MEDIUM",
        },
    },
    {
        "name": "Priyanka Patel",
        "dob": "2004-07-29",
        "guardian_name": "Kishore Patel",
        "apaar_id": "8271-9304",  # Malformed: 8 digits
        "institution_id": AICTE_INSTITUTION_CODE,
        "institution_name": AICTE_INSTITUTION_NAME,
        "program": "B.Tech Electrical Engineering",
        "verification_status": "UNVERIFIED",
        "review_status": "REQUIRES_CORRECTION",
        "discrepancy": {
            "field": "apaar_id",
            "existing": "8271-9304",
            "proposed": "8271-9304-1029",
            "reason": "Identifier format error: Expected exactly 12 digits, found 8 digits.",
            "score": 0.0,
            "severity": "CRITICAL",
        },
    },
    {
        "name": "Aditya Nair",
        "dob": "2003-12-04",
        "guardian_name": "Gopal Nair",
        "apaar_id": "9823-ABCD-4019",  # Malformed: Contains letters
        "institution_id": AICTE_INSTITUTION_CODE,
        "institution_name": AICTE_INSTITUTION_NAME,
        "program": "B.Tech Chemical Engineering",
        "verification_status": "UNVERIFIED",
        "review_status": "REQUIRES_CORRECTION",
        "discrepancy": {
            "field": "apaar_id",
            "existing": "9823-ABCD-4019",
            "proposed": "9823-1024-4019",
            "reason": "Identifier contains non-numeric characters.",
            "score": 0.0,
            "severity": "CRITICAL",
        },
    },
    {
        "name": "Sneha Deshmukh",
        "dob": "2004-04-18",
        "guardian_name": "Anand Deshmukh",
        "apaar_id": "6728-1920-3847",
        "institution_id": AICTE_INSTITUTION_CODE,
        "institution_name": AICTE_INSTITUTION_NAME,
        "program": "B.Tech Computer Science & Engineering",
        "verification_status": "DEMO_VERIFIED",
        "review_status": "APPROVED",
        "issue_credential": True,
    },
    {
        "name": "Vikram Malhotra",
        "dob": "2003-08-25",
        "guardian_name": "Harish Malhotra",
        "apaar_id": "7482-9103-8472",
        "institution_id": AICTE_INSTITUTION_CODE,
        "institution_name": AICTE_INSTITUTION_NAME,
        "program": "B.Tech Electrical Engineering",
        "verification_status": "DEMO_VERIFIED",
        "review_status": "APPROVED",
        "issue_revoked_credential": True,
    },
    {
        "name": "Kavita K. Reddy",
        "dob": "2004-10-10",
        "guardian_name": "K. Narayana Reddy",
        "apaar_id": "3829-4710-5829",
        "institution_id": AICTE_INSTITUTION_CODE,
        "institution_name": AICTE_INSTITUTION_NAME,
        "program": "B.Tech Biotechnology",
        "verification_status": "DEMO_VERIFIED",
        "review_status": "PENDING_REVIEW",
    },
    {
        "name": "Kavita Reddy",
        "dob": "2004-10-10",
        "guardian_name": "Katta Narayana Reddy",
        "apaar_id": "3829-4710-5829",
        "institution_id": AICTE_INSTITUTION_CODE,
        "institution_name": AICTE_INSTITUTION_NAME,
        "program": "B.Tech Biotechnology",
        "verification_status": "DEMO_VERIFIED",
        "review_status": "PENDING_REVIEW",
        "is_duplicate_with_index": 11,  # Kavita K. Reddy
    },
    {
        "name": "Meera Joshi",
        "dob": "2003-02-14",
        "guardian_name": "",  # Missing guardian
        "apaar_id": "5920-1839-4012",
        "institution_id": AICTE_INSTITUTION_CODE,
        "institution_name": AICTE_INSTITUTION_NAME,
        "program": "B.Tech Information Technology",
        "verification_status": "FORMAT_VALID",
        "review_status": "REQUIRES_CORRECTION",
        "discrepancy": {
            "field": "guardian_name",
            "existing": "",
            "proposed": "Naveen Joshi",
            "reason": "Missing mandatory field: Guardian name",
            "score": 0.0,
            "severity": "HIGH",
        },
    },
    {
        "name": "Ananya Sen",
        "dob": "2004-05-30",
        "guardian_name": "Subir Sen",
        "apaar_id": "8192-3049-5819",
        "institution_id": AICTE_INSTITUTION_CODE,
        "institution_name": AICTE_INSTITUTION_NAME,
        "program": "B.Tech Computer Science & Engineering",
        "verification_status": "DEMO_VERIFIED",
        "review_status": "APPROVED",
    },
    {
        "name": "Devendra Singh",
        "dob": "2003-07-07",
        "guardian_name": "Mahendra Singh",
        "apaar_id": "4910-2837-1920",
        "institution_id": AICTE_INSTITUTION_CODE,
        "institution_name": AICTE_INSTITUTION_NAME,
        "program": "B.Tech Mechanical Engineering",
        "verification_status": "DEMO_VERIFIED",
        "review_status": "APPROVED",
    },
]

DEMO_USERS = [
    {
        "username": "admin",
        "password": "admin123",
        "full_name": "Prof. S. R. Bhattacharya (Dean Academics)",
        "role": "INSTITUTION_ADMIN",
        "institution_id": AICTE_INSTITUTION_CODE,
    },
    {
        "username": "officer",
        "password": "officer123",
        "full_name": "Dr. Anjali Nair (Registrar & Verification Officer)",
        "role": "VERIFICATION_OFFICER",
        "institution_id": AICTE_INSTITUTION_CODE,
    },
    {
        "username": "student",
        "password": "student123",
        "full_name": "Aarav Sharma (Student)",
        "role": "STUDENT",
        "institution_id": AICTE_INSTITUTION_CODE,
    },
]

from app.db.database import get_db, init_db

def seed_database(reset: bool = True):
    """
    Seeds database with complete synthetic demonstration data, pre-calculated hash-chained audit log,
    discrepancy items, duplicate candidate pairs, and signed demonstration credentials.
    """
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()

        if reset:
            cursor.execute("DELETE FROM credentials;")
            cursor.execute("DELETE FROM duplicate_candidates;")
            cursor.execute("DELETE FROM discrepancies;")
            cursor.execute("DELETE FROM students;")
            cursor.execute("DELETE FROM users;")
            cursor.execute("DELETE FROM audit_log;")
            cursor.execute("DELETE FROM sqlite_sequence;")

        # 1. Seed Demo Users
        for user in DEMO_USERS:
            pw_hash = get_password_hash(user["password"])
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, full_name, role, institution_id)
                VALUES (?, ?, ?, ?, ?);
                """,
                (user["username"], pw_hash, user["full_name"], user["role"], user["institution_id"]),
            )

        # Initialize Audit Chain with Genesis Block
        prev_hash = GENESIS_HASH
        base_time = datetime.now(timezone.utc) - timedelta(days=5)

        # Initial genesis audit event
        genesis_entry = create_audit_entry_payload(
            previous_hash=prev_hash,
            actor_id="system_init",
            actor_role="SYSTEM",
            action_type="SYSTEM_INITIALIZED",
            record_id="GENESIS",
            details={"system": "SAMANVAY SIH 2026", "mode": "DEMO_MODE", "version": "1.0.0"},
            custom_timestamp=base_time.isoformat(),
        )
        cursor.execute(
            """
            INSERT INTO audit_log (timestamp, actor_id, actor_role, action_type, record_id, details_json, previous_hash, entry_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                genesis_entry["timestamp"],
                genesis_entry["actor_id"],
                genesis_entry["actor_role"],
                genesis_entry["action_type"],
                genesis_entry["record_id"],
                genesis_entry["details_json"],
                genesis_entry["previous_hash"],
                genesis_entry["entry_hash"],
            ),
        )
        prev_hash = genesis_entry["entry_hash"]

        inserted_students = []

        # 2. Seed Student Records
        for idx, student in enumerate(SYNTHETIC_STUDENTS):
            norm_name = normalize_name(student["name"])["normalized"]
            blind_index = generate_blind_index(student["apaar_id"])

            cursor.execute(
                """
                INSERT INTO students (apaar_id, name, normalized_name, dob, guardian_name, institution_id, institution_name, program, verification_status, review_status, apaar_blind_index)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    student["apaar_id"],
                    student["name"],
                    norm_name,
                    student["dob"],
                    student["guardian_name"],
                    student["institution_id"],
                    student["institution_name"],
                    student["program"],
                    student["verification_status"],
                    student["review_status"],
                    blind_index,
                ),
            )
            student_id = cursor.lastrowid
            student_record = dict(student)
            student_record["id"] = student_id
            inserted_students.append(student_record)

            # Record student creation in audit log
            entry_time = (base_time + timedelta(hours=idx * 2)).isoformat()
            audit_entry = create_audit_entry_payload(
                previous_hash=prev_hash,
                actor_id="admin",
                actor_role="INSTITUTION_ADMIN",
                action_type="RECORD_CREATED",
                record_id=str(student_id),
                details={
                    "name": student["name"],
                    "apaar_masked": student["apaar_id"][-4:] if len(student["apaar_id"]) >= 4 else "FORMAT_ERR",
                    "status": student["verification_status"],
                },
                custom_timestamp=entry_time,
            )
            cursor.execute(
                """
                INSERT INTO audit_log (timestamp, actor_id, actor_role, action_type, record_id, details_json, previous_hash, entry_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    audit_entry["timestamp"],
                    audit_entry["actor_id"],
                    audit_entry["actor_role"],
                    audit_entry["action_type"],
                    audit_entry["record_id"],
                    audit_entry["details_json"],
                    audit_entry["previous_hash"],
                    audit_entry["entry_hash"],
                ),
            )
            prev_hash = audit_entry["entry_hash"]

            # Discrepancy insertion if applicable
            if "discrepancy" in student:
                disc = student["discrepancy"]
                is_resolved = disc.get("resolved", False)
                rev_status = "ACCEPTED_CORRECTION" if is_resolved else "UNRESOLVED"
                cursor.execute(
                    """
                    INSERT INTO discrepancies (student_id, field_name, existing_value, proposed_value, flag_reason, similarity_score, severity, review_status, reviewer_id, resolved_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        student_id,
                        disc["field"],
                        disc["existing"],
                        disc["proposed"],
                        disc["reason"],
                        disc["score"],
                        disc["severity"],
                        rev_status,
                        "officer" if is_resolved else None,
                        entry_time if is_resolved else None,
                    ),
                )
                disc_id = cursor.lastrowid

                # Record discrepancy in audit log
                audit_disc = create_audit_entry_payload(
                    previous_hash=prev_hash,
                    actor_id="system_reconciliation",
                    actor_role="SYSTEM",
                    action_type="DISCREPANCY_FLAGGED",
                    record_id=str(disc_id),
                    details={"student_id": student_id, "field": disc["field"], "reason": disc["reason"]},
                    custom_timestamp=entry_time,
                )
                cursor.execute(
                    """
                    INSERT INTO audit_log (timestamp, actor_id, actor_role, action_type, record_id, details_json, previous_hash, entry_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        audit_disc["timestamp"],
                        audit_disc["actor_id"],
                        audit_disc["actor_role"],
                        audit_disc["action_type"],
                        audit_disc["record_id"],
                        audit_disc["details_json"],
                        audit_disc["previous_hash"],
                        audit_disc["entry_hash"],
                    ),
                )
                prev_hash = audit_disc["entry_hash"]

        # 3. Seed Duplicate Candidates (e.g. Arun Kumar vs Arun Kumaar, and Kavita Reddy)
        duplicate_pairs = [
            (
                inserted_students[2]["id"],  # Arun Kumar (AICTE-IN-101)
                inserted_students[3]["id"],  # Arun Kumaar (AICTE-MH-204 - Pune)
                94.5,
                {"name": 91.0, "dob": 100.0, "guardian": 100.0, "apaar": 100.0},
                ["Identical APAAR Identifier", "Exact Date of Birth match", "Cross-institution dual enrollment risk"],
                True,
            ),
            (
                inserted_students[11]["id"],  # Kavita K. Reddy
                inserted_students[12]["id"],  # Kavita Reddy
                92.0,
                {"name": 88.0, "dob": 100.0, "guardian": 85.0, "apaar": 100.0},
                ["Identical APAAR Identifier", "Exact Date of Birth match", "High name similarity"],
                False,
            ),
        ]

        for s_a_id, s_b_id, comp_score, scores, reasons, cross_inst in duplicate_pairs:
            cursor.execute(
                """
                INSERT INTO duplicate_candidates (student_a_id, student_b_id, composite_score, field_scores_json, flag_reasons_json, is_cross_institution, review_decision)
                VALUES (?, ?, ?, ?, ?, ?, 'NEEDS_FURTHER_REVIEW');
                """,
                (s_a_id, s_b_id, comp_score, json.dumps(scores), json.dumps(reasons), cross_inst),
            )
            dup_id = cursor.lastrowid
            audit_dup = create_audit_entry_payload(
                previous_hash=prev_hash,
                actor_id="system_dedup",
                actor_role="SYSTEM",
                action_type="DUPLICATE_CANDIDATE_DETECTED",
                record_id=str(dup_id),
                details={"student_a": s_a_id, "student_b": s_b_id, "score": comp_score},
            )
            cursor.execute(
                """
                INSERT INTO audit_log (timestamp, actor_id, actor_role, action_type, record_id, details_json, previous_hash, entry_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    audit_dup["timestamp"],
                    audit_dup["actor_id"],
                    audit_dup["actor_role"],
                    audit_dup["action_type"],
                    audit_dup["record_id"],
                    audit_dup["details_json"],
                    audit_dup["previous_hash"],
                    audit_dup["entry_hash"],
                ),
            )
            prev_hash = audit_dup["entry_hash"]

        # 4. Seed Ed25519 Demonstration Credentials
        # A) Sneha Deshmukh: Active Valid Credential
        sneha = inserted_students[9]
        cred_valid = issue_demo_credential(sneha)
        cursor.execute(
            """
            INSERT INTO credentials (credential_id, student_id, canonical_json, signature, qr_payload_json, issued_at, expires_at, is_revoked)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0);
            """,
            (
                cred_valid["credential_id"],
                sneha["id"],
                cred_valid["canonical_json"],
                cred_valid["signature"],
                cred_valid["qr_payload_json"],
                cred_valid["issued_at"],
                cred_valid["expires_at"],
            ),
        )
        audit_cred1 = create_audit_entry_payload(
            previous_hash=prev_hash,
            actor_id="admin",
            actor_role="INSTITUTION_ADMIN",
            action_type="CREDENTIAL_ISSUED",
            record_id=cred_valid["credential_id"],
            details={"student_name": sneha["name"], "status": "ACTIVE"},
        )
        cursor.execute(
            """
            INSERT INTO audit_log (timestamp, actor_id, actor_role, action_type, record_id, details_json, previous_hash, entry_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                audit_cred1["timestamp"],
                audit_cred1["actor_id"],
                audit_cred1["actor_role"],
                audit_cred1["action_type"],
                audit_cred1["record_id"],
                audit_cred1["details_json"],
                audit_cred1["previous_hash"],
                audit_cred1["entry_hash"],
            ),
        )
        prev_hash = audit_cred1["entry_hash"]

        # B) Vikram Malhotra: Revoked Credential for Demonstration
        vikram = inserted_students[10]
        cred_revoked = issue_demo_credential(vikram)
        revoked_at = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO credentials (credential_id, student_id, canonical_json, signature, qr_payload_json, issued_at, expires_at, is_revoked, revocation_reason, revoked_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 'Dual enrollment detected across institutions. Revoked pending AICTE committee verification.', ?);
            """,
            (
                cred_revoked["credential_id"],
                vikram["id"],
                cred_revoked["canonical_json"],
                cred_revoked["signature"],
                cred_revoked["qr_payload_json"],
                cred_revoked["issued_at"],
                cred_revoked["expires_at"],
                revoked_at,
            ),
        )
        audit_cred2 = create_audit_entry_payload(
            previous_hash=prev_hash,
            actor_id="admin",
            actor_role="INSTITUTION_ADMIN",
            action_type="CREDENTIAL_REVOKED",
            record_id=cred_revoked["credential_id"],
            details={"student_name": vikram["name"], "reason": "Dual enrollment detected across institutions."},
            custom_timestamp=revoked_at,
        )
        cursor.execute(
            """
            INSERT INTO audit_log (timestamp, actor_id, actor_role, action_type, record_id, details_json, previous_hash, entry_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                audit_cred2["timestamp"],
                audit_cred2["actor_id"],
                audit_cred2["actor_role"],
                audit_cred2["action_type"],
                audit_cred2["record_id"],
                audit_cred2["details_json"],
                audit_cred2["previous_hash"],
                audit_cred2["entry_hash"],
            ),
        )
        prev_hash = audit_cred2["entry_hash"]

    return {
        "status": "success",
        "message": f"Successfully seeded {len(SYNTHETIC_STUDENTS)} synthetic student records, audit entries, and demo credentials.",
    }
