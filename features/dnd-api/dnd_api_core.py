#!/usr/bin/env python3
"""
D&D 5e API Core - Simple request wrapper
Just makes requests and returns JSON. Nothing fancy.
"""

import json
import os
import re
import sys
import tempfile
import urllib.request
import urllib.error
from pathlib import Path

API_HOST = "https://www.dnd5eapi.co"
BASE_URL = f"{API_HOST}/api/2014"
CACHE_DIR = Path(__file__).parent / "cache"

def _cache_path(endpoint):
    """Cache file for an endpoint (SRD 2014 data is immutable, so no TTL)"""
    return CACHE_DIR / (re.sub(r"[^A-Za-z0-9]+", "_", endpoint).strip("_") + ".json")

def fetch(endpoint):
    """Fetch data from D&D API and return as dict (disk-cached)"""
    # Callers pass either a path under /api/2014 or a full API path (spell scripts)
    url = f"{API_HOST}{endpoint}" if endpoint.startswith("/api/") else f"{BASE_URL}{endpoint}"
    cached = _cache_path(endpoint)
    if cached.exists():
        try:
            return json.loads(cached.read_text())
        except (ValueError, OSError):
            pass  # corrupt or unreadable cache file: refetch and overwrite it

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "message": e.reason}
    except Exception as e:
        return {"error": "Request failed", "message": str(e)}

    CACHE_DIR.mkdir(exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=CACHE_DIR, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f)
    os.replace(tmp, cached)
    return data

def output(data):
    """Output data as JSON to stdout"""
    print(json.dumps(data, indent=2))

def error_output(message):
    """Output error in consistent format"""
    output({"error": message})
    sys.exit(1)

if __name__ == "__main__":
    goblin = _cache_path("/monsters/goblin")

    first = fetch("/monsters/goblin")
    assert first.get("name") == "Goblin", first
    assert goblin.exists()

    # A cache hit must not touch the network. NetworkUsed derives from BaseException
    # so fetch's `except Exception` cannot swallow it.
    class NetworkUsed(BaseException):
        pass

    def _no_network(*a, **kw):
        raise NetworkUsed("network call on a cache hit")

    real_urlopen = urllib.request.urlopen
    urllib.request.urlopen = _no_network
    try:
        assert fetch("/monsters/goblin") == first
    finally:
        urllib.request.urlopen = real_urlopen

    # A corrupt cache file must not brick the endpoint: refetch and overwrite.
    goblin.write_text("{not json")
    assert fetch("/monsters/goblin").get("name") == "Goblin"
    assert json.loads(goblin.read_text()).get("name") == "Goblin"

    # A real HTTP error still returns as before and caches nothing (live call).
    missing = fetch("/monsters/definitely-not-a-monster")
    assert missing["error"] == "HTTP 404", missing
    assert not _cache_path("/monsters/definitely-not-a-monster").exists()

    print("dnd_api_core self-check: OK")