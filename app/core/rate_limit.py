"""Per-IP rate limits (PROPOSAL §9.8, §10.4)."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# In-memory counters: they reset when the process restarts and are not shared between
# instances, which is fine for the one-instance deployment (PROPOSAL §10.4).
# The IP is request.client.host; uvicorn fills it from X-Forwarded-For because the
# Dockerfile runs it with --proxy-headers --forwarded-allow-ips '*'.
limiter = Limiter(key_func=get_remote_address)

LOGIN_LIMIT = "5/minute"
REGISTER_LIMIT = "3/minute"
