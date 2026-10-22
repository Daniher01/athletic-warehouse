import hashlib
import hmac

from warehouse_backend.infrastructure.auth.hmac_verifier import verify_tableflow_hmac_signature


def test_verify_tableflow_hmac_signature_valid() -> None:
    secret = "my-secret-key"
    payload = b'{"hello": "world"}'
    valid_sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    assert verify_tableflow_hmac_signature(payload, secret, valid_sig) is True


def test_verify_tableflow_hmac_signature_with_prefix() -> None:
    secret = "my-secret-key"
    payload = b'{"records": [1, 2, 3]}'
    raw_sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    prefixed_sig = f"sha256={raw_sig}"

    assert verify_tableflow_hmac_signature(payload, secret, prefixed_sig) is True


def test_verify_tableflow_hmac_signature_tampered_payload() -> None:
    secret = "my-secret-key"
    payload = b'{"amount": 100}'
    tampered = b'{"amount": 1000}'
    sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    assert verify_tableflow_hmac_signature(tampered, secret, sig) is False


def test_verify_tableflow_hmac_signature_wrong_secret() -> None:
    secret1 = "secret-1"
    secret2 = "secret-2"
    payload = b'{"test": true}'
    sig = hmac.new(secret1.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    assert verify_tableflow_hmac_signature(payload, secret2, sig) is False


def test_verify_tableflow_hmac_signature_empty_inputs() -> None:
    assert verify_tableflow_hmac_signature(b"data", "", "some_sig") is False
    assert verify_tableflow_hmac_signature(b"data", "secret", "") is False
    assert verify_tableflow_hmac_signature(b"data", "secret", None) is False
