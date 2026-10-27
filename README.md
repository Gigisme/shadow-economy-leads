# Shadow Economy Leads: Vilnius

A pipeline that surfaces **shadow-economy signals** among Vilnius businesses:
places that look **busy to the public** (Google Maps) but **quiet on paper**
(official Lithuanian registers).

The output is a **prioritised, explainable lead list** for a State Tax
Inspectorate (VMI) analyst with limited inspection capacity. A café with
2,000 Google reviews and a weekend queue that declares one employee is worth a
closer look; a quiet corner shop with one employee is not.

> These are **leads, not accusations**. The design deliberately trades recall
> for precision: an honest business wrongly flagged costs an inspection and
> trust, so uncertain cases go to a *review* tier instead of the lead list.

> This is a hypothetical scenario built as a technical exercise.

## Requirements this project meets

- **Visible activity** comes from Google Maps, collected with Python.
- **Declared activity** comes from official Lithuanian public sources.
- At least **3 business categories** in Vilnius.
- A real lead list from real, recent data, where every lead can be **traced**
  to its listing and official records and **explained** (why it scored as it did).
- The analyst can ask **their own questions** of the data without re-running the pipeline.
- **Monthly runs** that can be compared over time.
- **Containerised:** runs with a single command on a clean machine.

## Data sources

| Source | What we take | Access |
|---|---|---|
| **Google Maps** | venues per category; reviews, rating, opening hours, website | Oxylabs scraper API |
| **Google Maps** | verification of candidate venues: still open, website, review count | Google Places API (New) |
| **Registrų centras** (Register Centre) | registered and deregistered companies | [registrucentras.lt](https://www.registrucentras.lt) direct CSV downloads |
| **Registrų centras** (Register Centre) | annual profit/loss statements | [data.gov.lt](https://data.gov.lt) API |
| **VMI** (State Tax Inspectorate) | taxes paid per company per month | [data.gov.lt](https://data.gov.lt) API |
| **Sodra** (State Social Insurance Fund) | insured employees, average wage, activity code per company per month | [atvira.sodra.lt](https://atvira.sodra.lt) bulk files |

Glossary, diagrams and data model: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Status

Work in progress. Planned build order:

1. Design: architecture, data model *(done)*
2. Ingest: Registrų centras, VMI, Sodra
3. Ingest: Google Maps
4. Matching Google listings to companies, plus a hand-labelled evaluation
5. Features, scoring, safety gates, lead history
6. Data quality checks
7. Analyst app and example output from a real run
8. `DECISIONS.md`: design decisions, rejected alternatives, limitations

## Quick start

*Coming with step 7.*
