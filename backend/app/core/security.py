import base64
import hashlib
import hmac
import os
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from app.core.config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    HMAC_SECRET_KEY,
    ED25519_PRIVATE_KEY_PATH,
    ED25519_PUBLIC_KEY_PATH,
)

# ==============================================================================
# 1. ED25519 ASYMMETRIC DIGITAL SIGNATURES (RFC 8032)
# ==============================================================================

def init_ed25519_keys():
    """Initializes Ed25519 institutional signing keys if not already present."""
    if not ED25519_PRIVATE_KEY_PATH.exists() or not ED25519_PUBLIC_KEY_PATH.exists():
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        with open(ED25519_PRIVATE_KEY_PATH, "wb") as f:
            f.write(private_bytes)
        with open(ED25519_PUBLIC_KEY_PATH, "wb") as f:
            f.write(public_bytes)

def get_ed25519_private_key() -> ed25519.Ed25519PrivateKey:
    init_ed25519_keys()
    with open(ED25519_PRIVATE_KEY_PATH, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)

def get_ed25519_public_key() -> ed25519.Ed25519PublicKey:
    init_ed25519_keys()
    with open(ED25519_PUBLIC_KEY_PATH, "rb") as f:
        return serialization.load_pem_public_key(f.read())

def get_public_key_pem() -> str:
    init_ed25519_keys()
    with open(ED25519_PUBLIC_KEY_PATH, "r") as f:
        return f.read()

def sign_data(data: bytes) -> str:
    """Signs bytes using institutional Ed25519 private key. Returns Base64URL string."""
    private_key = get_ed25519_private_key()
    raw_sig = private_key.sign(data)
    return base64.urlsafe_b64encode(raw_sig).decode("utf-8").rstrip("=")

def verify_signature(data: bytes, signature_b64: str) -> bool:
    """Verifies Base64URL signature against institutional Ed25519 public key."""
    try:
        public_key = get_ed25519_public_key()
        # Pad base64url if needed
        padding = "=" * ((4 - len(signature_b64) % 4) % 4)
        sig_bytes = base64.urlsafe_b64decode(signature_b64 + padding)
        public_key.verify(sig_bytes, data)
        return True
    except Exception:
        return False

# ==============================================================================
# 2. KEYED HMAC BLIND INDEXING (Privacy-Preserving Record Linkage)
# ==============================================================================

def generate_blind_index(raw_identifier: str) -> str:
    """
    Computes a deterministic, server-side keyed HMAC-SHA256 blind index.
    Allows institutional equality queries without exposing raw APAAR or national IDs.
    """
    clean_id = "".join(filter(str.isalnum, raw_identifier.strip().upper()))
    key_bytes = HMAC_SECRET_KEY.encode("utf-8")
    return hmac.new(key_bytes, clean_id.encode("utf-8"), hashlib.sha256).hexdigest()

# ==============================================================================
# 3. PASSWORD HASHING (PBKDF2-HMAC-SHA256)
# ==============================================================================

def get_password_hash(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{salt.hex()}:{key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        salt_hex, key_hex = hashed_password.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)
        actual_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100_000)
        return hmac.compare_digest(expected_key, actual_key)
    except Exception:
        return False

# ==============================================================================
# 4. JWT & ROLE-BASED ACCESS CONTROL (RBAC)
# ==============================================================================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None
