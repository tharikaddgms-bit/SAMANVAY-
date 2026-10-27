from typing import Dict, Any, List, Optional, Tuple
from rapidfuzz import fuzz
from app.core.normalization import normalize_name, normalize_dob, validate_apaar_format

# Common phonetic and transliteration equivalents in Indian names
PHONETIC_PAIRS = [
    ("EE", "I"),
    ("OO", "U"),
    ("AA", "A"),
    ("SH", "S"),
    ("CH", "C"),
    ("TH", "T"),
    ("BH", "B"),
    ("DH", "D"),
    ("GH", "G"),
    ("KH", "K"),
    ("PH", "F"),
    ("V", "W"),
    ("KS", "X"),
]

def apply_phonetic_normalization(name: str) -> str:
    """Applies common Indian English transliteration soundex-like folding."""
    s = name.upper()
    for source, target in PHONETIC_PAIRS:
        s = s.replace(source, target)
    return s

def calculate_name_similarity(name1: str, name2: str) -> Dict[str, Any]:
    """
    Computes fine-grained multi-metric string similarity between two names using RapidFuzz.
    Returns composite score (0-100), metric breakdown, and explanation.
    """
    norm1 = normalize_name(name1)["normalized"]
    norm2 = normalize_name(name2)["normalized"]

    if not norm1 or not norm2:
        return {
            "score": 0.0,
            "is_exact": False,
            "metrics": {"ratio": 0, "token_sort": 0, "partial": 0, "phonetic_ratio": 0},
            "explanation": "One or both names are empty.",
        }

    if norm1 == norm2:
        return {
            "score": 100.0,
            "is_exact": True,
            "metrics": {"ratio": 100, "token_sort": 100, "partial": 100, "phonetic_ratio": 100},
            "explanation": "Exact normalized match.",
        }

    ratio = fuzz.ratio(norm1, norm2)
    token_sort = fuzz.token_sort_ratio(norm1, norm2)
    partial = fuzz.partial_ratio(norm1, norm2)

    phon1 = apply_phonetic_normalization(norm1)
    phon2 = apply_phonetic_normalization(norm2)
    phonetic_ratio = fuzz.ratio(phon1, phon2)

    # Weighted composite score
    composite = (token_sort * 0.45) + (ratio * 0.25) + (phonetic_ratio * 0.20) + (partial * 0.10)
    composite = round(min(100.0, max(0.0, composite)), 1)

    explanation_parts = []
    if token_sort >= 90:
        explanation_parts.append("Tokens match with minor character variation")
    elif phonetic_ratio >= 88:
        explanation_parts.append("Phonetically very similar transliteration (e.g., ee/i or oo/u)")
    elif partial >= 90:
        explanation_parts.append("One name appears as a substring/abbreviation of the other")
    else:
        explanation_parts.append(f"Substantial variation (score: {composite}%)")

    return {
        "score": composite,
        "is_exact": False,
        "metrics": {
            "ratio": ratio,
            "token_sort": token_sort,
            "partial": partial,
            "phonetic_ratio": phonetic_ratio,
        },
        "explanation": "; ".join(explanation_parts),
    }

def check_dob_transposition(dob1: str, dob2: str) -> Tuple[bool, str]:
    """
    Checks if two YYYY-MM-DD dates exhibit day/month transposition (e.g. 2003-05-12 vs 2003-12-05).
    """
    if dob1 == dob2:
        return True, "EXACT_MATCH"

    try:
        parts1 = dob1.split("-")
        parts2 = dob2.split("-")
        if len(parts1) == 3 and len(parts2) == 3:
            # Same year, swapped month and day
            if parts1[0] == parts2[0] and parts1[1] == parts2[2] and parts1[2] == parts2[1]:
                return True, "DAY_MONTH_TRANSPOSITION"
    except Exception:
        pass

    return False, "MISMATCH"

def detect_discrepancies_for_record(
    existing: Dict[str, Any],
    proposed: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Compares an existing student record with an incoming/proposed batch record and identifies field-level discrepancies.
    """
    discrepancies = []

    # 1. Student Name
    name_check = calculate_name_similarity(existing.get("name", ""), proposed.get("name", ""))
    if name_check["score"] < 100.0:
        discrepancies.append({
            "field": "name",
            "existing_value": existing.get("name", ""),
            "proposed_value": proposed.get("name", ""),
            "similarity_score": name_check["score"],
            "flag_reason": f"Name spelling variation detected ({name_check['explanation']})",
            "severity": "HIGH" if name_check["score"] < 75 else "MEDIUM",
        })

    # 2. Date of Birth
    exist_dob_norm = normalize_dob(existing.get("dob", ""))
    prop_dob_norm = normalize_dob(proposed.get("dob", ""))

    if exist_dob_norm["canonical"] != prop_dob_norm["canonical"]:
        is_transp, reason = check_dob_transposition(
            exist_dob_norm["canonical"], prop_dob_norm["canonical"]
        )
        flag_reason = (
            "Day-Month transposition likely (e.g., DD/MM vs MM/DD)"
            if is_transp
            else "Date of birth discrepancy"
        )
        discrepancies.append({
            "field": "dob",
            "existing_value": existing.get("dob", ""),
            "proposed_value": proposed.get("dob", ""),
            "similarity_score": 85.0 if is_transp else 0.0,
            "flag_reason": flag_reason,
            "severity": "HIGH",
        })

    # 3. Guardian Name
    if existing.get("guardian_name") and proposed.get("guardian_name"):
        guard_check = calculate_name_similarity(
            existing.get("guardian_name", ""), proposed.get("guardian_name", "")
        )
        if guard_check["score"] < 100.0:
            discrepancies.append({
                "field": "guardian_name",
                "existing_value": existing.get("guardian_name", ""),
                "proposed_value": proposed.get("guardian_name", ""),
                "similarity_score": guard_check["score"],
                "flag_reason": f"Guardian name difference ({guard_check['explanation']})",
                "severity": "MEDIUM",
            })

    # 4. APAAR ID format
    apaar_check = validate_apaar_format(existing.get("apaar_id", ""))
    if not apaar_check["is_valid"]:
        discrepancies.append({
            "field": "apaar_id",
            "existing_value": existing.get("apaar_id", ""),
            "proposed_value": proposed.get("apaar_id", ""),
            "similarity_score": 0.0,
            "flag_reason": f"Identifier format error: {apaar_check['error_reason']}",
            "severity": "CRITICAL",
        })

    return discrepancies

def compute_duplicate_candidate_score(
    record_a: Dict[str, Any],
    record_b: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Compares two student records (within same institute or across institutes)
    and computes a composite duplicate candidate score with explanation.
    Never merges or modifies records automatically.
    """
    if record_a.get("id") == record_b.get("id"):
        return None

    # Name similarity
    name_sim = calculate_name_similarity(record_a.get("name", ""), record_b.get("name", ""))
    name_score = name_sim["score"]

    # Guardian similarity
    guard_sim = calculate_name_similarity(
        record_a.get("guardian_name", ""), record_b.get("guardian_name", "")
    )
    guard_score = guard_sim["score"]

    # DOB match
    dob_a = normalize_dob(record_a.get("dob", ""))["canonical"]
    dob_b = normalize_dob(record_b.get("dob", ""))["canonical"]
    dob_exact = (dob_a == dob_b and bool(dob_a))
    is_transp, transp_reason = check_dob_transposition(dob_a, dob_b)

    if dob_exact:
        dob_score = 100.0
    elif is_transp:
        dob_score = 80.0
    else:
        dob_score = 10.0

    # APAAR ID comparison
    id_a = validate_apaar_format(record_a.get("apaar_id", ""))["clean_id"]
    id_b = validate_apaar_format(record_b.get("apaar_id", ""))["clean_id"]
    same_apaar = bool(id_a and id_b and id_a == id_b)
    apaar_score = 100.0 if same_apaar else (fuzz.ratio(id_a, id_b) if id_a and id_b else 0.0)

    # Weighted composite score
    composite = (name_score * 0.40) + (guard_score * 0.20) + (dob_score * 0.25) + (apaar_score * 0.15)
    composite = round(composite, 1)

    flag_reasons = []
    if same_apaar:
        flag_reasons.append("Identical APAAR Identifier")
    if name_score >= 88.0:
        flag_reasons.append(f"High name similarity ({name_score}%)")
    if dob_exact:
        flag_reasons.append("Exact Date of Birth match")
    elif is_transp:
        flag_reasons.append("DOB transposition match")
    if guard_score >= 85.0:
        flag_reasons.append(f"Guardian name match ({guard_score}%)")

    # Flag cross-institution dual enrollment risk
    is_cross_institution = record_a.get("institution_id") != record_b.get("institution_id")
    if is_cross_institution:
        flag_reasons.append(
            f"Cross-institution candidate ({record_a.get('institution_id')} vs {record_b.get('institution_id')})"
        )

    # Threshold for flagging as candidate
    if composite >= 68.0 or same_apaar:
        return {
            "record_a_id": record_a.get("id"),
            "record_b_id": record_b.get("id"),
            "record_a_name": record_a.get("name"),
            "record_b_name": record_b.get("name"),
            "record_a_inst": record_a.get("institution_id"),
            "record_b_inst": record_b.get("institution_id"),
            "composite_score": composite,
            "field_scores": {
                "name": name_score,
                "guardian": guard_score,
                "dob": dob_score,
                "apaar": apaar_score,
            },
            "flag_reasons": flag_reasons,
            "is_cross_institution": is_cross_institution,
        }

    return None
