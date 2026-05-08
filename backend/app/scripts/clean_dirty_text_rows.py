"""Find and clean dirty article/event rows in Supabase that contain JS/code artifacts.

Usage:
    python -m app.scripts.clean_dirty_text_rows [--dry-run] [--table event_analyses|shared_ticker_events|all]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.pipeline.analysis_utils import _is_code_like_text, _SCRIPT_TAG_RE, _JSON_LD_RE, sanitize_text_field
from app.services.supabase import get_supabase


_JS_INDICATORS = [
    "const ",
    "function",
    "document.",
    "window.",
    "localStorage",
    "bidRequests",
    "pubx",
    "prebid",
    "googletag",
    "__tcfapi",
    "var ",
    "module.exports",
    "require(",
    "webpackJsonp",
    "innerHTML",
    "outerHTML",
    ".addEventListener(",
    ".querySelector",
    ".getElementById",
    "console.log",
    "return {",
]


def _looks_dirty(text: str) -> bool:
    if not text:
        return False
    if _is_code_like_text(text):
        return True
    for indicator in _JS_INDICATORS:
        if indicator in text:
            return True
    if "<script" in text.lower():
        return True
    if _SCRIPT_TAG_RE.search(text):
        return True
    if _JSON_LD_RE.search(text):
        return True
    return False


def _clean_row_text(value: str) -> str:
    cleaned = sanitize_text_field(value)
    return cleaned


def scan_table(supabase, table: str, text_columns: list[str], dry_run: bool = True) -> list[dict]:
    print(f"\n=== Scanning {table} ===")
    dirty_rows = []
    batch_size = 200
    offset = 0
    while True:
        result = (
            supabase.table(table)
            .select(",".join(["id"] + text_columns))
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            break
        for row in rows:
            for col in text_columns:
                val = row.get(col, "") or ""
                if _looks_dirty(str(val)):
                    cleaned = _clean_row_text(str(val))
                    dirty_rows.append({
                        "table": table,
                        "id": row["id"],
                        "column": col,
                        "dirty_preview": str(val)[:200],
                        "cleaned_preview": cleaned[:200],
                        "cleaned_is_empty": not cleaned,
                    })
        offset += batch_size
        if len(rows) < batch_size:
            break
    print(f"Found {len(dirty_rows)} dirty text cells in {table}")
    for entry in dirty_rows[:10]:
        status = "WOULD CLEAN" if dry_run else "CLEANED"
        empty_marker = " -> EMPTY (would need title fallback)" if entry["cleaned_is_empty"] else ""
        print(f"  {status}: {table}/{entry['column']}/{entry['id']}: {entry['dirty_preview'][:80]}...{empty_marker}")
    if len(dirty_rows) > 10:
        print(f"  ... and {len(dirty_rows) - 10} more")
    return dirty_rows


def clean_table(supabase, table: str, text_columns: list[str], dirty_rows: list[dict]) -> int:
    cleaned_count = 0
    for entry in dirty_rows:
        col = entry["column"]
        if entry["cleaned_is_empty"]:
            cleaned_value = None
        else:
            cleaned_value = entry.get("cleaned_preview")
            if not cleaned_value:
                cleaned_value = None
        supabase.table(table).update({col: cleaned_value}).eq("id", entry["id"]).execute()
        cleaned_count += 1
    return cleaned_count


TEXT_COLUMNS = {
    "event_analyses": ["title", "summary", "long_analysis", "scenario_summary", "source"],
    "shared_ticker_events": ["title", "summary", "source", "body"],
}


def main():
    parser = argparse.ArgumentParser(description="Find and clean dirty article/event rows")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Only scan, don't update")
    parser.add_argument("--apply", action="store_true", help="Actually update dirty rows")
    parser.add_argument("--table", choices=["event_analyses", "shared_ticker_events", "all"], default="all")
    args = parser.parse_args()

    supabase = get_supabase()
    tables = list(TEXT_COLUMNS.keys()) if args.table == "all" else [args.table]
    all_dirty = []

    for table in tables:
        cols = TEXT_COLUMNS[table]
        dirty = scan_table(supabase, table, cols, dry_run=not args.apply)
        all_dirty.extend(dirty)

    if not args.apply:
        print(f"\n[DRY RUN] Found {len(all_dirty)} dirty text cells total.")
        print("Run with --apply to clean them.")
    else:
        print(f"\nApplying cleanup to {len(all_dirty)} dirty text cells...")
        by_table = {}
        for entry in all_dirty:
            by_table.setdefault(entry["table"], []).append(entry)
        for table, entries in by_table.items():
            cols = TEXT_COLUMNS[table]
            count = clean_table(supabase, table, cols, entries)
            print(f"  Cleaned {count} cells in {table}")
        print("Done.")


if __name__ == "__main__":
    main()
