"""Optional public secondary-source discovery. One fixed HTTPS service, no URL fetch API."""

from datetime import datetime, timezone
from urllib.parse import quote

HOST = "https://en.wikipedia.org"
LIMIT = 500_000


def request_json(path, params=None):
    if not path.startswith(
        ("/w/rest.php/v1/search/page", "/api/rest_v1/page/summary/")
    ):
        raise ValueError("Unsupported Wikimedia endpoint")
    import httpx

    # Redirects are rejected; user inputs never choose the host, scheme or port.
    with httpx.Client(
        timeout=20,
        follow_redirects=False,
        headers={
            "User-Agent": "ClaimEvidencePortfolio/0.1 (educational local evidence review)"
        },
    ) as client:
        with client.stream("GET", HOST + path, params=params) as response:
            response.raise_for_status()
            if response.status_code != 200:
                raise ValueError("Unexpected Wikimedia response")
            chunks = []
            size = 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > LIMIT:
                    raise ValueError("Wikimedia response too large")
                chunks.append(chunk)
    import json

    return json.loads(b"".join(chunks))


def discover(query, consent=False, fetch=request_json):
    if consent is not True:
        raise ValueError(
            "Explicit approval required before sending this query to Wikimedia"
        )
    if (
        not isinstance(query, str)
        or not 2 <= len(query.strip()) <= 160
        or any(ord(c) < 32 for c in query)
    ):
        raise ValueError("Query must contain 2–160 printable characters")
    results = fetch("/w/rest.php/v1/search/page", {"q": query.strip(), "limit": 3})
    sources = []
    failures = []
    for page in results.get("pages", [])[:3]:
        key = page.get("key")
        if not isinstance(key, str) or not key or len(key) > 300:
            continue
        try:
            result = fetch("/api/rest_v1/page/summary/" + quote(key, safe=""))
            text = result.get("extract")
            if not isinstance(text, str) or not text.strip():
                raise ValueError("No readable summary")
            sources.append(
                dict(
                    title=str(result.get("title", key))[:300],
                    url=HOST + "/wiki/" + quote(key, safe=""),
                    text=text[:12000],
                    origin="Wikimedia summary retrieved automatically; secondary source, not primary-source verification",
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                    last_modified_at=result.get("timestamp"),
                    license="Wikipedia text: CC BY-SA; see linked article history and license terms",
                )
            )
        except Exception:
            failures.append(key + " summary unavailable; no source was fabricated")
    return dict(
        query=query,
        sources=sources,
        failures=failures,
        notice="Queries were sent only to Wikimedia. Summaries are starting points, not independent confirmation; consult primary sources before adjudicating.",
    )
