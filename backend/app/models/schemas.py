from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

# Authentication
class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    institution_id: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Student Records
class StudentRecordCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    dob: str = Field(..., description="Date of birth in YYYY-MM-DD or DD/MM/YYYY")
    guardian_name: Optional[str] = Field(None, max_length=200)
    apaar_id: str = Field(..., description="12-digit numeric APAAR identifier")
    institution_id: Optional[str] = "AICTE-IN-101"
    institution_name: Optional[str] = "Delhi Technological Institute (Autonomous)"
    program: Optional[str] = "B.Tech Computer Science & Engineering"

class StudentRecordUpdate(BaseModel):
    name: Optional[str] = None
    dob: Optional[str] = None
    guardian_name: Optional[str] = None
    apaar_id: Optional[str] = None
    program: Optional[str] = None
    verification_status: Optional[str] = None
    review_status: Optional[str] = None

class StudentRecordResponse(BaseModel):
    id: int
    apaar_id: str
    name: str
    normalized_name: str
    dob: str
    guardian_name: Optional[str]
    institution_id: str
    institution_name: str
    program: str
    verification_status: str
    review_status: str
    apaar_blind_index: str
    created_at: str
    updated_at: str

# Discrepancy Reconciliation
class DiscrepancyReviewRequest(BaseModel):
    decision: str = Field(
        ...,
        description="Action: ACCEPT_CORRECTION, REJECT_CORRECTION, REQUEST_INFO, LEAVE_UNRESOLVED",
    )
    notes: Optional[str] = None
    custom_corrected_value: Optional[str] = None

# Duplicate Detection
class DuplicateCandidateReviewRequest(BaseModel):
    decision: str = Field(
        ...,
        description="Action: CONFIRMED_MATCH, NOT_A_MATCH, NEEDS_FURTHER_REVIEW",
    )
    notes: Optional[str] = None

# Credentials
class CredentialIssueRequest(BaseModel):
    student_id: int
    validity_days: Optional[int] = 365

class CredentialRevocationRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500)

class PublicCredentialVerifyRequest(BaseModel):
    credential_id: Optional[str] = None
    canonical_json: Optional[str] = None
    signature: Optional[str] = None
