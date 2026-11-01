import base64
import hashlib
import hmac
import json
import math
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from src.core.config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    """Hashea una contraseña usando PBKDF2-HMAC-SHA256 con salt seguro."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"pbkdf2_sha256${salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña en texto plano coincide con el hash almacenado."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 3 or parts[0] != "pbkdf2_sha256":
            return False

        _, salt, expected_key = parts
        computed = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            100_000,
        )
        return hmac.compare_digest(computed.hex(), expected_key)
    except Exception:
        return False


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Genera un token JWT (HS256) estándar con tiempo de expiración."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "jti": secrets.token_urlsafe(32),
    })

    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _base64url_encode(json.dumps(to_encode, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """Valida y decodifica el token JWT. Lanza ValueError si es inválido o expiró."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Formato de token JWT inválido.")

    header_b64, payload_b64, signature_b64 = parts
    header = json.loads(_base64url_decode(header_b64).decode("utf-8"))
    if not isinstance(header, dict) or header.get("alg") != "HS256":
        raise ValueError("Algoritmo de token JWT inválido.")
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    expected_sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(_base64url_encode(expected_sig), signature_b64):
        raise ValueError("Firma criptográfica del token inválida.")

    payload = json.loads(_base64url_decode(payload_b64).decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Contenido de token JWT inválido.")
    exp = payload.get("exp")
    if (
        isinstance(exp, bool)
        or not isinstance(exp, (int, float))
        or (isinstance(exp, float) and not math.isfinite(exp))
        or exp > 253402300799
        or exp <= datetime.now(timezone.utc).timestamp()
    ):
        raise ValueError("El token ha expirado o no tiene una expiración válida.")

    return payload

