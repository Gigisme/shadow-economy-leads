"""Registrų centras company register: registered and deregistered companies (daily CSVs)."""

from pathlib import Path

from shadow_leads.ingest.http import FileSpec, fetch_files

SOURCE = "registrucentras"
BASE_URL = "https://www.registrucentras.lt/aduomenys/?byla="
FILES = ("JAR_IREGISTRUOTI.csv", "JAR_ISREGISTRUOTI.csv")
CSV_HEADER_START = b"ja_kodas|"


def fetch(run_id: str) -> Path:
    return fetch_files(SOURCE, run_id, [FileSpec(BASE_URL + name, name, CSV_HEADER_START) for name in FILES])
