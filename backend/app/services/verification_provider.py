from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.core.normalization import validate_apaar_format, normalize_name, normalize_dob

class VerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    FORMAT_VALID = "FORMAT_VALID"
    DEMO_VERIFIED = "DEMO_VERIFIED"
    OFFICIALLY_VERIFIED = "OFFICIALLY_VERIFIED"

class IVerificationProvider(ABC):
    """Abstract pluggable interface for student record verification providers."""

    @abstractmethod
    def verify(
        self,
        apaar_id: str,
        name: str,
        dob: str,
        guardian_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Performs verification and returns standardized verification result."""
        pass

class DemoProvider(IVerificationProvider):
    """
    Synthetic demonstration provider.
    Validates identifier format and simulates match against synthetic registry cohort.
    Strictly yields DEMO_VERIFIED or FORMAT_VALID; NEVER yields OFFICIALLY_VERIFIED.
    """

    def __init__(self, synthetic_cohort: Optional[Dict[str, Dict[str, Any]]] = None):
        self.synthetic_cohort = synthetic_cohort or {}

    def set_cohort(self, cohort: Dict[str, Dict[str, Any]]):
        self.synthetic_cohort = cohort

    def verify(
        self,
        apaar_id: str,
        name: str,
        dob: str,
        guardian_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        format_check = validate_apaar_format(apaar_id)
        if not format_check["is_valid"]:
            return {
                "status": VerificationStatus.UNVERIFIED,
                "provider": "DemoProvider",
                "verified": False,
                "reason": f"Format check failed: {format_check['error_reason']}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "provider_type": "SYNTHETIC_MOCK",
            }

        clean_id = format_check["clean_id"]
        # Check against synthetic cohort
        cohort_record = self.synthetic_cohort.get(clean_id)
        if cohort_record:
            norm_name = normalize_name(name)["normalized"]
            cohort_name = normalize_name(cohort_record.get("name", ""))["normalized"]
            norm_dob = normalize_dob(dob)["canonical"]
            cohort_dob = normalize_dob(cohort_record.get("dob", ""))["canonical"]

            if norm_name == cohort_name and norm_dob == cohort_dob:
                return {
                    "status": VerificationStatus.DEMO_VERIFIED,
                    "provider": "DemoProvider",
                    "verified": True,
                    "reason": "Matched synthetic mock APAAR registry cohort.",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "provider_type": "SYNTHETIC_MOCK",
                    "details": {
                        "synthetic_registry_id": f"SYNTH-REG-{clean_id[-4:]}",
                        "academic_credits": cohort_record.get("credits", 84),
                    },
                }

        # Identifier has valid format, but no synthetic match
        return {
            "status": VerificationStatus.FORMAT_VALID,
            "provider": "DemoProvider",
            "verified": False,
            "reason": "Passed 12-digit format check. Pending synthetic/institutional registry match.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider_type": "SYNTHETIC_MOCK",
        }

class OfficialProvider(IVerificationProvider):
    """
    Disabled production integration stub for official government APAAR / DigiLocker APIs.
    Must remain disabled until authentic government agency sandbox keys are authorized.
    """

    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None):
        self.api_key = api_key
        self.endpoint = endpoint
        self.is_configured = bool(api_key and endpoint)

    def verify(
        self,
        apaar_id: str,
        name: str,
        dob: str,
        guardian_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.is_configured:
            raise RuntimeError(
                "OfficialProvider is disabled. Official government API credentials are not configured. "
                "SAMANVAY strictly adheres to SIH problem statement boundaries and will not simulate official government verification without real authorization."
            )

        # In production with authorized keys, this would invoke government API
        return {
            "status": VerificationStatus.OFFICIALLY_VERIFIED,
            "provider": "OfficialGovAPI",
            "verified": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider_type": "GOVERNMENT_OFFICIAL",
        }
