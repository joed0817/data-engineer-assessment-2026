# Data Engineer Assessment

**Candidate:** [Jose De La Cruz]
**Submitted:** April 27, 2026


---

## 🔗 Live Dashboard

**[View the live Streamlit dashboard →](https://jdlc-data-engineer.streamlit.app)**

---

## 📐 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     DATA SOURCES                            │
│  Homebuilder_Sales.csv (600 rows)  +  Regional_Lookup.xlsx  │
└──────────────────────┬──────────────────────────────────────┘
                       │  COPY INTO / UI Upload
                       ▼
┌─────────────────────────────────────────────────────────────┐
│             SNOWFLAKE — RHODES_ASSESSMENT DB                 │
│                                                             │
│  RAW schema                                                 │
│  ├── HOMEBUILDER_SALES        (600 rows, CSV)               │
│  └── REGIONAL_MANAGER_TARGETS  (3 rows, CSV)              │
│                                                             │
│  STAGING schema (dbt views — no storage cost)               │
│  ├── stg_homebuilder_sales    (typed, flagged, enriched)    │
│  └── stg_regional_manager_targets                            │
│                                                             │
│  MARTS schema (dbt tables — pre-aggregated for speed)       │
│  ├── mart_sales_performance   (1 row/contract, all KPIs)    │
│  ├── mart_community_summary   (rollup by community)         │
│  ├── mart_consultant_perf     (leaderboard model)           │
│  └── cortex_regional_summaries (Cortex AI output)           │
└──────────────────────┬──────────────────────────────────────┘
                       │
          ┌────────────┴──────────────┐
          │                           │
          ▼                           ▼
   dbt Cloud                  Snowflake Cortex
   (Transformation)           (AI Summaries via COMPLETE)
                                       │
                                       ▼
                            ┌──────────────────────┐
                            │  Streamlit Dashboard  │
                            │  + Claude NL Query    │
                            └──────────────────────┘
```

---

## 📁 Project Structure

```
data-engineer-assessment-2026/
│
├── ingestion/
│   ├── 01_setup_schemas.sql          # Database, schema, warehouse setup
│   ├── 02_create_tables_and_load.sql # Table DDL + COPY INTO
│   └── 03_cortex_ai_summaries.sql    # Cortex COMPLETE — regional AI summaries
│
├── dbt_project/
│   ├── dbt_project.yml               # dbt project config
│   ├── profiles.yml                  # Snowflake connection (reference only)
│   └── models/
│       ├── staging/
│       │   ├── sources.yml                      # Raw source declarations
│       │   ├── schema.yml                       # Staging model docs + tests
│       │   ├── stg_homebuilder_sales.sql
│       │   └── stg_regional_manager_targets.sql
│       └── marts/
│           ├── schema.yml                       # Mart model docs + tests
│           ├── mart_sales_performance.sql        # Primary analysis model
│           ├── mart_community_summary.sql        # Community rollup
│           └── mart_consultant_performance.sql   # Consultant leaderboard
│
├── streamlit_app/
│   ├── app.py                        # Full dashboard application
│   ├── requirements.txt
│   └── .streamlit/
│       └── secrets.toml              # Credentials (not committed to git)
│
├── .gitignore
└── README.md
```

---

## 🏗️ Pipeline Decisions

### Schema Design
Three-schema architecture in a single Snowflake database:
- **RAW** — untouched source data, loaded once, never modified by transformation code
- **STAGING** — materialized as views (zero storage cost), handles all type casting, flag derivation, and string normalization
- **MARTS** — materialized as tables for query performance; these are what the dashboard and Cortex queries hit

This separation means the dashboard never reads raw data directly, and the staging layer can be rebuilt without touching the mart queries.

### dbt Modeling Decisions

**Staging layer** cleans without joining. Each staging model maps 1:1 to a source table. Key work done here:
- `TRY_TO_DATE()` instead of `TO_DATE()` — prevents hard failures on malformed dates (the brief noted synthetic data may have inconsistencies)
- Derived boolean flags (`is_closed`, `is_cancelled`, `is_under_contract`) make downstream SQL much cleaner than repeated `CASE WHEN STATUS = ...` everywhere
- `days_to_close_calc` recalculated from parsed dates to validate the raw field — a useful data quality check
- All strings `TRIM()`-ed to prevent join failures from invisible whitespace

**Mart layer** joins and aggregates. `mart_sales_performance` is the single source of truth — one row per contract with all enrichment applied. The two rollup marts (`mart_community_summary`, `mart_consultant_performance`) pre-aggregate so the dashboard renders instantly without scanning 600 rows on every filter change.

### Cortex AI Choice
Used `CORTEX.COMPLETE` with `mistral-7b` to generate two outputs per region:
1. An executive summary (3 sentences, highlighting strength and risk)
2. Recommended action items (2 data-driven bullet points)

Results are stored as a table rather than called live, which keeps dashboard load times fast and avoids repeated Cortex credit usage. The model is prompted with specific numeric context from the mart aggregates rather than raw rows, which produces more consistent and accurate outputs.

### Natural Language Query
The NL query feature uses Claude (Anthropic) grounded in a pre-built data context summary. Rather than sending all 600 raw rows (expensive, often redundant), the context is built from the community and consultant rollup tables plus high-level dataset stats. This gives the model accurate, current numbers while keeping token usage low. Multi-turn conversation history is maintained in Streamlit session state.

---

## 🚀 Running Locally

```bash
# Clone the repo
git clone https://github.com/joed0817/data-engineer-assessment-2026.git
cd rhodes-data-engineer-assessment

# Install Streamlit deps
pip install -r streamlit_app/requirements.txt

# Set up secrets in Streamlit for Snowflake and Claude

# Run the dashboard
streamlit run streamlit_app/app.py
```

### dbt (local) - for on-prem deployments
```bash
pip install dbt-snowflake
##cp dbt_project/profiles.yml ~/.dbt/profiles.yml
# Edit with your Snowflake credentials

cd dbt_project
dbt deps
dbt run
dbt test
```

---

## 📊 Dataset

| File | Rows | Description |
|------|------|-------------|
| `Homebuilder_Sales.csv` | 600 | Sales contracts across 8 communities, 3 regions, 6 consultants (2023–2024) |
| `Regional_Manager_Lookup.xlsx` | 3 | Regional managers and annual unit/margin targets |

Key data notes:
- 528 Closed, 41 Cancelled, 31 Under Contract
- `close_date` and `days_to_close` are NULL for Cancelled and Under Contract records (expected)
- Data is synthetic and provided by Rhodes Enterprises for assessment purposes

---

## 🤔 If I Had More Time

- **Snowflake Cortex FORECAST** — predict next quarter's closings by community using the ML function; 
- **dbt tests** — expand beyond the basics to include range tests (price > 0, sqft > 500), referential integrity, and custom test for margin calculation reasonableness
- **Incremental dbt models** — `mart_sales_performance` would benefit from incremental materialization in a production environment with daily data loads
- **Row-level security** — in production, regional managers should only see their own region's data; Snowflake row access policies would handle this
- **Alert automation** — a Snowflake Task + Streamlit notification when cancellation rate exceeds threshold by community
