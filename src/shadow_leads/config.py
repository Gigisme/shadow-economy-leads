"""Project-wide settings: paths, scope and categories."""

import os
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(os.environ.get("SHADOW_LEADS_DATA_DIR", "data"))
RAW_DIR = DATA_DIR / "raw"

# Sodra spells the municipality this way; used to scope declared data to Vilnius city.
VILNIUS_MUNICIPALITY = "Vilniaus m. sav."

USER_AGENT = "shadow-economy-leads/0.1 (research project; +https://github.com/Gigisme/shadow-economy-leads)"


@dataclass(frozen=True)
class Category:
    key: str
    label: str
    google_queries: tuple[str, ...]
    activity_codes: tuple[str, ...]  # EVRK / NACE Rev. 2.1, as Sodra reports them


CATEGORIES: tuple[Category, ...] = (
    Category("restaurant", "Restaurants & cafés", ("restaurant", "cafe"), ("56.11",)),
    Category("bar", "Bars", ("bar", "pub"), ("56.30", "56.11")),
    Category("beauty", "Hair & beauty salons", ("hair salon", "barber shop", "beauty salon"), ("96.21", "96.22")),
    Category("car_repair", "Car repair", ("car repair", "auto service"), ("95.31",)),
    Category("car_wash", "Car washes", ("car wash",), ("95.31",)),
)
