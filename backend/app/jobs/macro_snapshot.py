from app.pipeline.macro_snapshot import refresh_macro_snapshot


def run() -> dict:
    ok = refresh_macro_snapshot()
    return {
        "status": "completed" if ok else "failed",
        "items_processed": 1 if ok else 0,
        "items_failed": 0 if ok else 1,
    }
