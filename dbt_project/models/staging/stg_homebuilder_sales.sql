-- ============================================================
-- Model: stg_homebuilder_sales
-- Layer: Staging
-- Materialization: View (no storage cost, always fresh)
--
-- Purpose: Clean and standardize raw sales data. Cast types,
-- add derived boolean flags, and normalize strings. No joins
-- at this layer — just source fidelity + light transformation.
-- ============================================================

WITH source AS (

    SELECT * FROM {{ source('raw', 'homebuilder_sales') }}

),

cleaned AS (

    SELECT
        -- ── Identity ───────────────────────────────────────────
        CONTRACT_ID                                                 AS contract_id,

        -- ── Geography & Segmentation ────────────────────────────
        TRIM(COMMUNITY)                                             AS community,
        TRIM(CITY)                                                  AS city,
        TRIM(REGION)                                                AS region,
        TRIM(PLAN_NAME)                                             AS plan_name,

        -- ── Home Specs ──────────────────────────────────────────
        SQFT                                                        AS sqft,
        BEDROOMS                                                    AS bedrooms,
        BATHROOMS                                                   AS bathrooms,

        -- ── Financials ──────────────────────────────────────────
        BASE_PRICE                                                  AS base_price,
        UPGRADE_AMOUNT                                              AS upgrade_amount,
        INCENTIVE_AMOUNT                                            AS incentive_amount,
        CONTRACT_PRICE                                              AS contract_price,

        -- Derived: gross upgrade attach rate (upgrades as % of base price)
        ROUND(
            CASE WHEN BASE_PRICE > 0 THEN UPGRADE_AMOUNT / BASE_PRICE ELSE NULL END,
            4
        )                                                           AS upgrade_attach_rate,

        -- Derived: net incentive rate (incentives as % of contract price)
        ROUND(
            CASE WHEN CONTRACT_PRICE > 0 THEN INCENTIVE_AMOUNT / CONTRACT_PRICE ELSE NULL END,
            4
        )                                                           AS incentive_rate,

        -- ── Dates ───────────────────────────────────────────────
        TRY_TO_DATE(CONTRACT_DATE, 'YYYY-MM-DD')                   AS contract_date,
        TRY_TO_DATE(CLOSE_DATE, 'YYYY-MM-DD')                      AS close_date,  -- NULL for open/cancelled

        -- Recalculated days to close from parsed dates (validates raw field)
        DATEDIFF('day',
            TRY_TO_DATE(CONTRACT_DATE, 'YYYY-MM-DD'),
            TRY_TO_DATE(CLOSE_DATE, 'YYYY-MM-DD')
        )                                                           AS days_to_close_calc,

        -- Original raw days_to_close for reference
        DAYS_TO_CLOSE                                               AS days_to_close_raw,

        -- Extracted time dimensions for dashboarding
        YEAR(TRY_TO_DATE(CONTRACT_DATE, 'YYYY-MM-DD'))             AS contract_year,
        MONTH(TRY_TO_DATE(CONTRACT_DATE, 'YYYY-MM-DD'))            AS contract_month,
        MONTHNAME(TRY_TO_DATE(CONTRACT_DATE, 'YYYY-MM-DD'))        AS contract_month_name,
        DATE_TRUNC('month', TRY_TO_DATE(CONTRACT_DATE, 'YYYY-MM-DD')) AS contract_month_start,

        -- ── Status Flags ─────────────────────────────────────────
        TRIM(UPPER(STATUS))                                         AS status_raw,
        CASE WHEN UPPER(TRIM(STATUS)) = 'CLOSED'          THEN TRUE ELSE FALSE END AS is_closed,
        CASE WHEN UPPER(TRIM(STATUS)) = 'CANCELLED'       THEN TRUE ELSE FALSE END AS is_cancelled,
        CASE WHEN UPPER(TRIM(STATUS)) = 'UNDER CONTRACT'  THEN TRUE ELSE FALSE END AS is_under_contract,

        -- ── Lead Source & Financing ──────────────────────────────
        TRIM(BUYER_SOURCE)                                          AS buyer_source,
        TRIM(LOAN_TYPE)                                             AS loan_type,

        -- Derived: flag for agent-referred business
        CASE
            WHEN UPPER(TRIM(BUYER_SOURCE)) IN ('REALTOR REFERRAL', 'REPEAT/REFERRAL')
            THEN TRUE ELSE FALSE
        END                                                         AS is_referral,

        -- ── Sales Team ───────────────────────────────────────────
        TRIM(SALES_CONSULTANT)                                      AS sales_consultant,
        AGENT_COMMISSION                                            AS agent_commission

    FROM source

)

SELECT * FROM cleaned
