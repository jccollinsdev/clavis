from app.pipeline.sector_snapshot import SECTOR_ETFS, refresh_sector_snapshots


def run() -> dict:
    written = refresh_sector_snapshots()
    expected = len(SECTOR_ETFS)
    failed = max(0, expected - written)
    return {
        "status": "completed" if failed == 0 else "failed",
        "items_processed": written,
        "items_failed": failed,
        "metadata": {"expected_sectors": expected},
    }
