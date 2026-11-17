"""Transparent local candidate extraction and passage ranking, no LLM or remote calls."""

import hashlib
import ipaddress
import math
import re
from collections import Counter
from urllib.parse import urlsplit

STOP = set(
    "a an the and or but is are was were be been being to of in on at for by with from as it its that this these those has have had can could would should will may might do does did not no than then into about through".split()
)
ABBREVIATIONS = re.compile(
    r"\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|vs|etc|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|U\.S|U\.K|e\.g|i\.e)\.",
    re.I,
)


def tokens(text):
    return [
        t for t in re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text.lower()) if t not in STOP
    ]


def spans(text):
    masked = ABBREVIATIONS.sub(lambda m: m.group().replace(".", "\u2024"), text)
    start = 0
    for match in re.finditer(r'(?<=[.!?])\s+(?=[A-Z0-9"“])|\n+|;\s*', masked):
        end = match.start()
        if text[start:end].strip():
            a = start + len(text[start:end]) - len(text[start:end].lstrip())
            b = end - len(text[start:end]) + len(text[start:end].rstrip())
            yield a, b, text[a:b]
        start = match.end()
    if text[start:].strip():
        a = start + len(text[start:]) - len(text[start:].lstrip())
        b = len(text.rstrip())
        yield a, b, text[a:b]


def safe_url(value):
    if (
        not isinstance(value, str)
        or len(value) > 2048
        or any(ord(c) < 33 for c in value)
    ):
        return False
    try:
        u = urlsplit(value)
        if (
            u.scheme != "https"
            or not u.hostname
            or u.username
            or u.password
            or u.port not in (None, 443)
        ):
            return False
        h = u.hostname.lower()
        if (
            "." not in h
            or h.endswith((".local", ".internal", ".localhost"))
            or h == "localhost"
        ):
            return False
        try:
            if not ipaddress.ip_address(h).is_global:
                return False
        except ValueError:
            pass
        return True
    except ValueError:
        return False


def validate_sources(sources):
    if not isinstance(sources, list) or len(sources) > 12:
        raise ValueError("Use up to 12 source documents")
    clean = []
    seen = {}
    for i, s in enumerate(sources):
        if not isinstance(s, dict):
            raise ValueError("Each source must be an object")
        for key, limit in [("title", 300), ("text", 50000), ("url", 2048)]:
            if (
                not isinstance(s.get(key), str)
                or not s[key].strip()
                or len(s[key]) > limit
            ):
                raise ValueError("Source %s needs valid %s" % (i + 1, key))
        if not safe_url(s["url"]):
            raise ValueError(
                "Source links must be public HTTPS URLs without credentials or custom ports"
            )
        for key, limit in (
            ("origin", 1000),
            ("license", 2048),
            ("retrieved_at", 100),
            ("publication_date", 100),
            ("last_modified_at", 100),
        ):
            value = s.get(key)
            if value is not None and (not isinstance(value, str) or len(value) > limit):
                raise ValueError("Invalid source metadata: " + key)
        original = s.get("original_source")
        if original is not None:
            if not isinstance(original, dict) or not safe_url(original.get("url")):
                raise ValueError(
                    "Original source attribution requires a public HTTPS URL"
                )
            for key in ("title", "url", "license", "retrieved_at", "last_modified_at"):
                value = original.get(key)
                if value is not None and (
                    not isinstance(value, str) or len(value) > 2048
                ):
                    raise ValueError("Invalid original source metadata")
            original = {
                key: original.get(key)
                for key in (
                    "title",
                    "url",
                    "license",
                    "retrieved_at",
                    "last_modified_at",
                )
            }
        digest = hashlib.sha256(s["text"].encode()).hexdigest()
        if digest in seen:
            seen[digest]["aliases"].append(
                dict(
                    title=s["title"],
                    url=s["url"],
                    license=s.get("license"),
                    original_source=original,
                )
            )
            continue
        clean.append(
            dict(
                id="source-%02d" % (len(clean) + 1),
                title=s["title"],
                url=s["url"],
                text=s["text"],
                text_sha256=digest,
                origin=s.get("origin", "supplied text; not independently retrieved"),
                retrieved_at=s.get("retrieved_at"),
                publication_date=s.get("publication_date"),
                license=s.get("license"),
                last_modified_at=s.get("last_modified_at"),
                aliases=[],
                original_source=original,
            )
        )
        seen[digest] = clean[-1]
    return clean


def extract(text):
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 20000:
        raise ValueError("Response must contain 1–20,000 characters")
    result = []
    for a, b, sentence in spans(text):
        if len(result) >= 80:
            raise ValueError("Response has over 80 passages; use a shorter response")
        lower = sentence.lower()
        excluded = sentence.endswith("?") or bool(
            re.match(r"^(please |i (think|believe|prefer|love)|in my opinion)", lower)
        )
        checkable = bool(
            re.search(
                r"\b(is|are|was|were|has|have|began|begins|became|landed|launched|founded|contains|includes|costs|rose|fell|increased|decreased|requires|allows|prohibits)\b",
                lower,
            )
            or re.search(r"\d", sentence)
        )
        category = "candidate" if checkable and not excluded else "needs-scope-review"
        result.append(
            dict(
                id="claim-%03d" % (len(result) + 1),
                text=sentence,
                start=a,
                end=b,
                scope=category,
                reason=(
                    "Declarative/date/number heuristic; verify this is a factual claim."
                    if category == "candidate"
                    else "Question, opinion, instruction or unrecognized form; not automatically excluded from human review."
                ),
                compound=bool(re.search(r"\b(and|but|while|because)\b", lower)),
            )
        )
    return result


def analyze(text, sources):
    sources = validate_sources(sources)
    claims = extract(text)
    passages = []
    skipped_passages = 0
    for source in sources:
        for a, b, sentence in spans(source["text"]):
            if len(sentence) > 2000:
                skipped_passages += 1
                continue
            passages.append(
                dict(
                    id="passage-%04d" % (len(passages) + 1),
                    source_id=source["id"],
                    quote=sentence,
                    start=a,
                    end=b,
                )
            )
    if len(passages) > 4000:
        raise ValueError("Too many source passages; shorten the corpus")
    freq = Counter(t for p in passages for t in set(tokens(p["quote"])))
    idf = lambda t: math.log(1 + (len(passages) + 1) / (1 + freq[t]))
    for claim in claims:
        query = set(tokens(claim["text"]))
        denom = sum(idf(t) for t in query) or 1
        ranked = []
        for passage in passages:
            terms = set(tokens(passage["quote"]))
            shared = query & terms
            lexical = sum(idf(t) for t in shared) / denom
            if len(shared) < 2 or lexical < 0.15:
                continue
            cues = []
            expected = set(re.findall(r"\b\d+(?:[.,]\d+)*(?:%)?", claim["text"]))
            found = set(re.findall(r"\b\d+(?:[.,]\d+)*(?:%)?", passage["quote"]))
            if expected - found and found:
                cues.append(
                    dict(
                        kind="number-difference",
                        detail="Claim numbers absent from this passage: "
                        + ", ".join(sorted(expected - found))
                        + ". Passage numbers: "
                        + ", ".join(sorted(found))
                        + ". May refer to different events or quantities; not proof of contradiction.",
                    )
                )
            neg = lambda s: bool(
                re.search(
                    r"\b(no|not|never|cannot|can't|didn't|doesn't|isn't|wasn't)\b",
                    s.lower(),
                )
            )
            if neg(claim["text"]) != neg(passage["quote"]):
                cues.append(
                    dict(
                        kind="negation-difference",
                        detail="Negation wording differs. Scope and meaning must be checked manually.",
                    )
                )
            ranked.append(
                dict(
                    **passage,
                    lexical_relevance=round(lexical, 4),
                    shared_terms=sorted(shared),
                    cues=cues,
                    relation="unassessed"
                )
            )
        ranked.sort(key=lambda p: (-p["lexical_relevance"], p["id"]))
        claim["evidence"] = ranked[:4]
        claim["retrieval_status"] = (
            "passages-to-review" if ranked else "no-lexical-match"
        )
        claim["verdict"] = "unreviewed"
        claim["query"] = " ".join(tokens(claim["text"])[:12])[:160]
    return dict(
        schema_version=1,
        response=text,
        response_sha256=hashlib.sha256(text.encode()).hexdigest(),
        sources=sources,
        claims=claims,
        coverage=dict(
            indexed_passages=len(passages),
            skipped_long_passages=skipped_passages,
            duplicate_source_count=sum(len(s["aliases"]) for s in sources),
        ),
        method="English heuristic claim candidates + IDF-weighted lexical passage retrieval; no automatic truth verdict or calibrated accuracy score.",
        limits=[
            "Compound claims may remain together. Candidate extraction can miss implied facts.",
            "Lexical overlap is not evidence of support. Empty retrieval is not a false verdict.",
            "Numbers and negation cues may concern different entities, dates or scopes.",
            "Source origin, currency, independence and reliability require human review.",
        ],
    )
