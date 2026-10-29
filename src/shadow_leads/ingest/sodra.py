"""Sodra open company data: monthly insured count, average wage and contributions per employer."""

from pathlib import Path

from shadow_leads.ingest.http import FileSpec, fetch_files

SOURCE = "sodra"
URL = "https://atvira.sodra.lt/imones/downloads/{year}/monthly-{year}.csv.zip"
ZIP_MAGIC = b"PK\x03\x04"


def fetch(run_id: str) -> Path:
    """Fetch the run's year and the previous one, so every company has at least 12 months of history.

    The year comes from the run id (YYYY-MM or YYYY-MM-DD). Early in January the new year's
    file may not be published yet, so only the previous year is required.
    """
    year = int(run_id[:4])
    specs = [
        FileSpec(URL.format(year=y), f"monthly-{y}.csv.zip", ZIP_MAGIC, optional=(y == year))
        for y in (year - 1, year)
    ]
    return fetch_files(SOURCE, run_id, specs)
