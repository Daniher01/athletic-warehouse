import hashlib
import hmac


def verify_tableflow_hmac_signature(
    raw_body: bytes,
    secret: str,
    signature_header: str | None,
) -> bool:
    """Verify HMAC-SHA256 signature for incoming Tableflow webhook.

    Resistant to timing attacks using constant-time hmac.compare_digest.
    Supports raw hex digest or 'sha256=<hex>' prefix.
    """
    if not signature_header or not secret:
        return False

    cleaned_signature = signature_header.strip()
    if cleaned_signature.lower().startswith("sha256="):
        cleaned_signature = cleaned_signature[7:].strip()

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature.lower(), cleaned_signature.lower())
