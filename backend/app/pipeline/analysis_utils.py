import hashlib
import ast
import json
import re
from datetime import datetime, timezone
from typing import Any


_PUBLIC_ANALYSIS_REPLACEMENTS: list[tuple[str, str]] = [
    (
        r"\bfull_body read rather than a fully grounded article analysis\b",
        "provisional article read",
    ),
    (r"\bfully grounded article analysis\b", "provisional article read"),
    (r"\bfully supported analysis\b", "provisional article read"),
    (
        r"\bfull article coverage rather than a fully supported analysis\b",
        "provisional article read",
    ),
    (r"\bfull_body\b", "full article"),
    (r"\btitle_only\b", "headline-only"),
    (r"\bheadline_summary\b", "headline summary"),
    (r"\bevidence quality\b", "coverage depth"),
    (r"\blow-evidence\b", "low-confidence coverage"),
    (r"\bcurrent evidence is still incomplete\b", "limited coverage remains"),
    (r"\bevidence is still incomplete\b", "limited coverage remains"),
    (r"\barticle evidence\b", "article coverage"),
    (
        r"\bthe model did not provide a usable written rationale, so this summary was synthesized from the final dimension scores\b",
        "this summary was assembled from the final dimension scores",
    ),
    (r"\bfallback synthesis\b", "summary assembled"),
]


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clamp_score(value: Any, default: int = 50) -> int:
    try:
        numeric = int(round(float(value)))
    except (TypeError, ValueError):
        numeric = default
    return max(0, min(100, numeric))


def safe_json_loads(raw_text: str, default: Any) -> Any:
    try:
        return json.loads(raw_text)
    except (TypeError, json.JSONDecodeError):
        return default


def _try_parse_json_like(raw_text: str) -> Any:
    parsed = safe_json_loads(raw_text, None)
    if parsed is not None:
        return parsed

    cleaned = re.sub(r",(\s*[}\]])", r"\1", raw_text)
    parsed = safe_json_loads(cleaned, None)
    if parsed is not None:
        return parsed

    try:
        return ast.literal_eval(cleaned)
    except (ValueError, SyntaxError):
        return None


def _strip_model_wrappers(raw_text: str) -> str:
    if not isinstance(raw_text, str):
        return ""

    cleaned = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL)
    cleaned = re.sub(r"```json\s*", "```", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()

    fence_match = re.search(r"```\s*(.*?)\s*```", cleaned, flags=re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    return cleaned


def _balanced_json_spans(raw_text: str) -> list[str]:
    spans: list[str] = []
    length = len(raw_text)

    for start, opening in ((i, ch) for i, ch in enumerate(raw_text) if ch in "[{"):
        stack = [opening]
        in_string = False
        escaped = False

        for idx in range(start + 1, length):
            ch = raw_text[idx]

            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue

            if ch == '"':
                in_string = True
                continue

            if ch in "[{":
                stack.append(ch)
                continue

            if ch in "]}":
                if not stack:
                    break
                top = stack[-1]
                if (top == "{" and ch != "}") or (top == "[" and ch != "]"):
                    break
                stack.pop()
                if not stack:
                    spans.append(raw_text[start : idx + 1].strip())
                    break

        if spans:
            break

    return spans


def extract_json_value(raw_text: str, default: Any) -> Any:
    cleaned = _strip_model_wrappers(raw_text)
    parsed = _try_parse_json_like(cleaned)
    if parsed is not None:
        return parsed

    if not cleaned:
        return default

    for candidate in _balanced_json_spans(cleaned):
        parsed = _try_parse_json_like(candidate)
        if parsed is not None:
            return parsed

    return default


def extract_json_object(raw_text: str, default: Any) -> Any:
    parsed = extract_json_value(raw_text, None)
    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, list) and len(parsed) > 0:
        for item in parsed:
            if isinstance(item, dict):
                return item
    return default


def extract_json_list(raw_text: str, default: Any) -> Any:
    parsed = extract_json_value(raw_text, None)
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        for key in ("results", "scores", "items", "data", "payload", "output"):
            candidate = parsed.get(key)
            if isinstance(candidate, list):
                return candidate
        for value in parsed.values():
            if isinstance(value, list):
                return value
    return default


def make_event_hash(*parts: Any) -> str:
    payload = "||".join(str(part or "").strip().lower() for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sanitize_public_analysis_text(value: Any) -> Any:
    if isinstance(value, str):
        cleaned = value
        for pattern, replacement in _PUBLIC_ANALYSIS_REPLACEMENTS:
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned
    if isinstance(value, list):
        return [sanitize_public_analysis_text(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitize_public_analysis_text(item) for key, item in value.items()}
    return value
