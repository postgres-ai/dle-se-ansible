#!/usr/bin/env python3
import sys
import time
import json
import hmac
import hashlib
import base64


def b64url(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def make_jwt(secret: str, role: str) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "role": role,
        "iss": "supabase",
        "iat": now,
        # 10 years, for local/self-hosted convenience
        "exp": now + 10 * 365 * 24 * 3600,
    }

    signing_input = b".".join([
        b64url(json.dumps(header, separators=(",", ":")).encode()),
        b64url(json.dumps(payload, separators=(",", ":")).encode()),
    ])
    sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    token = signing_input + b"." + b64url(sig)
    return token.decode()


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: gen_jwt.py <secret> <role>", file=sys.stderr)
        return 2
    secret = sys.argv[1]
    role = sys.argv[2]
    print(make_jwt(secret, role))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
