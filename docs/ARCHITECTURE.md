# Architecture

Goal: a monthly, explainable, prioritised list of Vilnius businesses that look
**busy on Google** but **quiet on paper** (official Lithuanian registers), for a
VMI analyst with limited inspection capacity.

## Glossary

| Term | Meaning |
|---|---|
| **Company code** (`company_code`) | 9-digit legal entity code (*juridinio asmens kodas*) assigned by Registrų centras. The join key across all official sources. |
| **Activity code** (`activity_code`) | What the business does, from the **EVRK** classification (*Ekonominės veiklos rūšių klasifikatorius*), the Lithuanian edition of the EU **NACE** classification. E.g. `56.11` = restaurants, `96.21` = hairdressing. Sodra and VMI report it per company; since 2025 it is NACE Rev. 2.1. |
| **Insured count** | Number of people the company pays social insurance for (Sodra `numInsured`), our proxy for declared employees. |
| **Listing** | One Google Maps place (one physical venue). One company can have many listings (chains). |
| **Google providers** | Oxylabs finds venues and their activity; the Google Places API verifies a listing is still open and cross-checks its data. See below. |

## Categories

| Category | Google Maps search / types | Activity codes (EVRK / NACE 2.1) | Vilnius companies in Sodra, 2026-09 |
|---|---|---|---|
| Restaurants & cafés | restaurant, cafe | `56.11` | 670 |
| Bars | bar, pub | `56.30` (many bars are registered as `56.11`) | 69 |
| Hair & beauty salons | hair salon, barber, beauty salon | `96.21`, `96.22` | 89 + 167 |
| Car repair | car repair, auto service | `95.31` | 520 |
| Car washes | car wash | `95.31` (shared with car repair) | in the 520 above |

Car repair and car washes share one activity code, so the Google category, not
the register, decides which of the two a venue belongs to.

## Sources

| Source | Dataset | Access | Refresh | Used for |
|---|---|---|---|---|
| Google Maps | places by category in Vilnius | Oxylabs scraper API (Python) | every run | **visible** activity: reviews, rating, hours, website |
| Google Maps | details for candidate listings | Google Places API (New) | every run | verification: still open, website, review-count cross-check |
| Registrų centras | registered companies (`JAR_IREGISTRUOTI.csv`) | direct download, registrucentras.lt/aduomenys | daily | names, addresses, legal form, status, for matching |
| Registrų centras | deregistered companies (`JAR_ISREGISTRUOTI.csv`) | direct download, registrucentras.lt/aduomenys | daily | flag listings whose company no longer exists |
| Registrų centras | profit/loss statements (`datasets/gov/rc/jar/pelno_ataskaitos`) | data.gov.lt API (published there by Registrų centras; no direct file) | yearly, about 5-month lag | **declared** sales revenue |
| VMI | taxes paid by companies (`datasets/gov/vmi/ja_mokesciai`) | data.gov.lt API | monthly | **declared** taxes paid |
| Sodra | company insurance data (`monthly-YYYY.csv.zip`) | atvira.sodra.lt bulk file | monthly, about 1-month lag | **declared** employees, average wage, activity code |
| Business websites | footer / contacts page | polite HTTP fetch | every run | company code printed on site, for high-confidence matching |

## 1. Pipeline

```mermaid
flowchart LR
    subgraph Sources
        G[Google Maps<br/>Oxylabs: discovery<br/>Places API: verification]
        RC[Registrų centras<br/>companies: direct CSV<br/>profit statements: data.gov.lt]
        VMI[VMI<br/>taxes paid<br/>data.gov.lt]
        SOD[Sodra<br/>monthly insurance data<br/>atvira.sodra.lt]
        WEB[Business websites<br/>footer / contacts]
    end

    subgraph Raw["data/raw/&lt;source&gt;/&lt;run&gt;/ (one folder per run)"]
        RG[(google/)]
        RR[(registrucentras/)]
        RV[(vmi/)]
        RS[(sodra/)]
        RW[(web/)]
    end

    subgraph DuckDB["warehouse.duckdb"]
        STG[staging<br/>typed, cleaned,<br/>normalised names]
        MATCH[matching<br/>listing → company code<br/>+ confidence + evidence]
        FEAT[features<br/>busy / quiet signals]
        SCORE[scoring<br/>peer model per category<br/>+ safety gates]
        LEADS[leads +<br/>lead_history]
    end

    DQ{{quality checks<br/>fail / warn}}
    APP[Streamlit app<br/>lead list · drill-down · SQL]
    OUT[output/<br/>leads_YYYY-MM.csv<br/>report.html]

    G --> RG
    RC --> RR
    VMI --> RV
    SOD --> RS
    WEB --> RW
    RG & RR & RV & RS & RW --> STG
    STG --> MATCH --> FEAT --> SCORE --> LEADS
    STG -.-> DQ
    MATCH -.-> DQ
    SCORE -.-> DQ
    LEADS --> APP
    LEADS --> OUT
```

Two run modes:
- **replay** (default, `docker compose up`): rebuilds everything from a committed, filtered sample of the raw data (Vilnius, our categories only), so it needs no API keys.
- **live**: scrapes fresh data and writes a new `data/raw/<source>/<run>` folder.

### Google providers: two tools, two jobs

```mermaid
flowchart LR
    subgraph OX["Oxylabs: discovery + activity (stored monthly)"]
        OXS[google_maps searches<br/>category × Vilnius grid]
    end
    subgraph PA["Places API: identity + verification (not stored)"]
        PAD[Place Details by place_id<br/>businessStatus · website ·<br/>userRatingCount]
    end
    OXS --> RAWO[(data/raw/google/&lt;run&gt;/*.json)]
    RAWO --> N[google_listing_snapshot<br/>place_id · name · address · lat/lon ·<br/>review_count · rating · hours · website · types]
    N -- place_id --> PAD
    PAD --> V[verification, used at run time<br/>closed? → drop · website → matching ·<br/>review count agrees? → quality metric]
    V --> STG[staging]
    N --> STG
```

| | **Oxylabs** (Web Scraper API, `google_maps`) | **Google Places API (New)** |
|---|---|---|
| Job | **Discovery and visible activity**: find every venue per category across a Vilnius grid; review count, rating, hours, website | **Identity and verification** for listings Oxylabs found: is it still open (`businessStatus`), official website, official review count |
| Why this tool | Results can be kept as monthly history and committed as the example run | Official, stable API with a clean `businessStatus` that scraping lacks; fits the free monthly allowance because we call it only for candidate listings, not for discovery |
| What we store | Full raw response, every run | Only `place_id` (allowed by Google's terms) and derived flags for the current run; raw Places content is not kept long-term |
| If it is unavailable | Run fails: no visible-activity data | Run continues; leads lose the "verified open" flag and drop a tier |

Using the Places API only on listings that are already candidates keeps it in the
free tier and inside its terms, and gives us a second, independent read of review
counts that we report as a data quality metric (how often the two providers agree).

Assumption to verify in the Oxylabs trial: its results carry Google's `place_id`.
If they do not, the Places API lookup falls back to a Text Search on name + address,
and that link gets its own confidence score.

## 2. Matching a listing to a company

```mermaid
flowchart TD
    L[Google listing] --> W{Website shows a<br/>9-digit company code<br/>that exists in Registrų centras?}
    W -- yes --> H[HIGH confidence]
    W -- no --> NA{Fuzzy name match<br/>+ same address<br/>+ activity code fits category?}
    NA -- yes --> H2[MEDIUM-HIGH confidence]
    NA -- no --> N{Unique name match<br/>within category activity codes?}
    N -- yes --> LOW[LOW: manual review queue<br/>never a lead]
    N -- no --> U[UNMATCHED<br/>counted in quality metrics]
    H & H2 --> AGG[Aggregate per company code<br/>chains: sum of all locations]
```

## 3. Scoring and safety gates

```mermaid
flowchart TD
    E[Matched company] --> B[Busy signals<br/>log reviews · review growth · opening hours]
    E --> Q[Quiet signals<br/>insured count · avg wage near minimum ·<br/>revenue and taxes paid per venue]
    B & Q --> M[Peer model per category<br/>expected employees given busyness]
    M --> R[Residual: N× fewer employees<br/>than similar businesses]
    R --> G1{Match confidence ≥ medium-high?}
    G1 -- no --> X[Not a lead]
    G1 -- yes --> G2{Company active and<br/>more than 12 months of Sodra history?}
    G2 -- no --> X
    G2 -- yes --> G3{Residual beyond<br/>robust threshold?}
    G3 -- no --> X
    G3 -- yes --> G4{Data fresh and no<br/>known benign pattern?}
    G4 -- no --> RV[Review tier<br/>with caveat note]
    G4 -- yes --> T[Tier A / B lead<br/>+ reason codes]
```

Leads are leads, not accusations. Every gate exists because a false flag costs an
honest business an inspection, so ambiguous cases drop to *review*, not *lead*.

## 4. Data model

```mermaid
erDiagram
    RUN ||--o{ GOOGLE_LISTING_SNAPSHOT : ""
    RUN ||--o{ MATCH : ""
    RUN ||--o{ LEAD_SCORE : ""
    GOOGLE_LISTING ||--o{ GOOGLE_LISTING_SNAPSHOT : "observed in run"
    GOOGLE_LISTING ||--o{ MATCH : "linked by"
    RC_COMPANY ||--o{ MATCH : "linked to"
    RC_COMPANY ||--o{ SODRA_MONTHLY : "declares staff"
    RC_COMPANY ||--o{ VMI_TAXES_MONTHLY : "pays taxes"
    RC_COMPANY ||--o{ RC_FINANCIALS_YEARLY : "files accounts"
    RC_COMPANY ||--o{ LEAD_SCORE : "scored in run"
    LEAD_SCORE ||--o{ LEAD_HISTORY : "tracked over runs"

    RUN {
        string run_id PK
        date run_month
        string mode "replay | live"
        json source_versions
    }
    GOOGLE_LISTING {
        string place_id PK
        string name
        string address
        string google_category
        string category "restaurant | bar | beauty | car_repair | car_wash"
    }
    GOOGLE_LISTING_SNAPSHOT {
        string run_id FK
        string place_id FK
        bool verified_open "from Places API"
        int review_count
        float rating
        float weekly_open_hours
        string website
    }
    RC_COMPANY {
        string company_code PK
        string legal_name
        string registered_address
        string legal_form
        string status
        date registered_on
    }
    SODRA_MONTHLY {
        string company_code FK
        int month
        string activity_code
        int insured_count
        float avg_wage
        float contribution
    }
    VMI_TAXES_MONTHLY {
        string company_code FK
        int month
        float taxes_paid
    }
    RC_FINANCIALS_YEARLY {
        string company_code FK
        int year
        float sales_revenue
    }
    MATCH {
        string run_id FK
        string place_id FK
        string company_code FK
        string method "website | name_address | name_only"
        string confidence
        json evidence
    }
    LEAD_SCORE {
        string run_id FK
        string company_code FK
        float residual
        string tier "A | B | review"
        json signal_contributions
        json reason_codes
    }
    LEAD_HISTORY {
        string company_code FK
        string run_id FK
        string status "new | persisting | escalated | dropped"
    }
```
