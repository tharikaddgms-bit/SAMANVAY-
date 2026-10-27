import re
import unicodedata
from datetime import datetime
from typing import Dict, Any, Optional, List

HONORIFICS_PREFIX_PATTERN = re.compile(
    r"^(\s*(SHRI|SHREE|SMT|SHRIMATI|KUMARI|MR|MRS|MS|MISS|DR|LATE)\.?\s+)+",
    re.IGNORECASE,
)

def normalize_name(raw_name: Optional[str]) -> Dict[str, Any]:
    """
    Deterministically normalizes a student or guardian name:
    1. Unicode decomposition (NFKD) and ASCII folding.
    2. Removal of common honorific prefixes.
    3. Removal of punctuation (dots, commas, hyphens).
    4. Collapse whitespace sequences and trim.
    5. Standardize to UPPERCASE.
    """
    if not raw_name or not raw_name.strip():
        return {
            "original": raw_name or "",
            "normalized": "",
            "changes_applied": ["EMPTY_FIELD"],
            "is_empty": True,
        }

    original = raw_name
    changes = []

    # 1. Unicode decomposition
    normalized = unicodedata.normalize("NFKD", original)
    if normalized != original:
        changes.append("UNICODE_NORMALIZED")

    # 2. Case conversion to uppercase
    if normalized != normalized.upper():
        normalized = normalized.upper()
        changes.append("UPPERCASE_FOLDED")

    # 3. Strip redundant honorifics if present at beginning only
    no_honorifics = HONORIFICS_PREFIX_PATTERN.sub("", normalized).strip()
    if no_honorifics and no_honorifics != normalized:
        normalized = no_honorifics
        changes.append("HONORIFIC_STRIPPED")

    # 4. Remove punctuation
    cleaned_punct = re.sub(r"[.,\-_\'\"]+", " ", normalized)
    if cleaned_punct != normalized:
        normalized = cleaned_punct
        changes.append("PUNCTUATION_REMOVED")

    # 5. Collapse multiple whitespace and trim
    collapsed = re.sub(r"\s+", " ", normalized).strip()
    if collapsed != original.strip():
        changes.append("WHITESPACE_COLLAPSED")

    return {
        "original": original,
        "normalized": collapsed,
        "changes_applied": changes,
        "is_empty": False,
    }

def validate_apaar_format(raw_id: Optional[str]) -> Dict[str, Any]:
    """
    Validates APAAR (Automated Permanent Academic Account Registry) ID format.
    APAAR IDs are standard 12-digit numeric identifiers, commonly formatted as XXXX-XXXX-XXXX.
    """
    if not raw_id or not raw_id.strip():
        return {
            "original": raw_id or "",
            "clean_id": "",
            "formatted": "",
            "is_valid": False,
            "error_reason": "Identifier is missing or empty.",
        }

    raw = raw_id.strip()
    # Strip spaces and hyphens
    cleaned = re.sub(r"[\s\-]+", "", raw)

    if not cleaned.isdigit():
        return {
            "original": raw,
            "clean_id": cleaned,
            "formatted": raw,
            "is_valid": False,
            "error_reason": "Identifier contains non-numeric characters.",
        }

    if len(cleaned) != 12:
        return {
            "original": raw,
            "clean_id": cleaned,
            "formatted": raw,
            "is_valid": False,
            "error_reason": f"Expected exactly 12 digits, found {len(cleaned)} digits.",
        }

    # Format into standard 4-4-4 block format
    formatted = f"{cleaned[:4]}-{cleaned[4:8]}-{cleaned[8:]}"

    return {
        "original": raw,
        "clean_id": cleaned,
        "formatted": formatted,
        "is_valid": True,
        "error_reason": None,
    }

def normalize_dob(raw_dob: Optional[str]) -> Dict[str, Any]:
    """
    Parses and normalizes dates of birth to canonical ISO 8601 (YYYY-MM-DD).
    Supports DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, YYYY/MM/DD.
    """
    if not raw_dob or not raw_dob.strip():
        return {
            "original": raw_dob or "",
            "canonical": "",
            "is_valid": False,
            "error_reason": "Date of birth is missing.",
        }

    cleaned = raw_dob.strip()
    formats_to_try = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d.%m.%Y",
    ]

    for fmt in formats_to_try:
        try:
            dt = datetime.strptime(cleaned, fmt)
            # Sanity check: age between 10 and 100 years
            now = datetime.now()
            age_years = (now - dt).days / 365.25
            if age_years < 10 or age_years > 100:
                return {
                    "original": cleaned,
                    "canonical": dt.strftime("%Y-%m-%d"),
                    "is_valid": False,
                    "error_reason": f"Implausible student age: {age_years:.1f} years.",
                }
            return {
                "original": cleaned,
                "canonical": dt.strftime("%Y-%m-%d"),
                "is_valid": True,
                "error_reason": None,
            }
        except ValueError:
            continue

    return {
        "original": cleaned,
        "canonical": "",
        "is_valid": False,
        "error_reason": f"Unrecognized date format: '{cleaned}'. Expected YYYY-MM-DD or DD/MM/YYYY.",
    }
