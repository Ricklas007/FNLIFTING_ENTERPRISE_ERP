import base64
import hashlib
import hmac
import io
import secrets
import struct
import time
from urllib.parse import quote


def generate_totp_secret() -> str:
    """Return a Base32 secret compatible with authenticator apps."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _secret_bytes(secret: str) -> bytes:
    padded = secret.strip().replace(" ", "").upper()
    padded += "=" * (-len(padded) % 8)
    return base64.b32decode(padded, casefold=True)


def totp_code(secret: str, timestamp: int | None = None, interval: int = 30, digits: int = 6) -> str:
    counter = int((timestamp or int(time.time())) / interval)
    digest = hmac.new(_secret_bytes(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10 ** digits)).zfill(digits)


def verify_totp(secret: str, code: str, valid_window: int = 1) -> bool:
    cleaned = "".join(character for character in code if character.isdigit())
    if len(cleaned) != 6:
        return False
    now = int(time.time())
    for window in range(-valid_window, valid_window + 1):
        if hmac.compare_digest(totp_code(secret, now + window * 30), cleaned):
            return True
    return False


def provisioning_uri(secret: str, account: str, issuer: str = "FNLIFTING Enterprise ERP") -> str:
    label = quote(f"{issuer}:{account}")
    return f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30"


def qr_png_data_uri(value: str) -> str:
    import qrcode

    image = qrcode.make(value)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
