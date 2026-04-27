-- ============================================================
-- Data Engineer Assessment
-- Cortex AI: Regional Performance Summaries
--
-- Uses Snowflake Cortex COMPLETE to generate natural-language
-- performance summaries for each region. Output is stored as
-- a MARTS table so the Streamlit dashboard reads it directly
-- without re-invoking Cortex on every page load.
--
-- Run this AFTER your dbt models have been built successfully.
-- ============================================================

USE DATABASE ASSESSMENT;
USE WAREHOUSE COMPUTE_WH;

-- -------------------------------------------------------
-- Step 1: Build regional aggregates as a CTE input to Cortex
-- -------------------------------------------------------

CREATE OR REPLACE TABLE ASSESSMENT.MARTS.CORTEX_REGIONAL_SUMMARIES AS

WITH regional_agg AS (

    SELECT
        region,
        regional_manager,
        sales_target_units,
        margin_target_pct,

        COUNT(*)                                                        AS total_contracts,
        SUM(CASE WHEN is_closed         THEN 1 ELSE 0 END)             AS closed_units,
        SUM(CASE WHEN is_cancelled      THEN 1 ELSE 0 END)             AS cancelled_units,
        SUM(CASE WHEN is_under_contract THEN 1 ELSE 0 END)             AS pipeline_units,

        ROUND(
            SUM(CASE WHEN is_cancelled THEN 1 ELSE 0 END)
            / NULLIF(SUM(CASE WHEN is_closed OR is_cancelled THEN 1 ELSE 0 END), 0) * 100,
            1
        )                                                               AS cancellation_rate_pct,

        ROUND(AVG(CASE WHEN is_closed THEN contract_price ELSE NULL END), 0)   AS avg_contract_price,
        ROUND(AVG(CASE WHEN is_closed THEN price_per_sqft ELSE NULL END), 2)   AS avg_price_per_sqft,
        ROUND(AVG(CASE WHEN is_closed THEN days_to_close  ELSE NULL END), 0)   AS avg_days_to_close,
        ROUND(AVG(CASE WHEN is_closed THEN gross_margin_pct ELSE NULL END) * 100, 1) AS avg_gross_margin_pct,
        ROUND(closed_units / NULLIF(sales_target_units, 0) * 100, 1)           AS target_attainment_pct

    FROM ASSESSMENT.MARTS.MART_SALES_PERFORMANCE
    GROUP BY 1, 2, 3, 4

)

SELECT
    region,
    regional_manager,
    total_contracts,
    closed_units,
    cancelled_units,
    pipeline_units,
    sales_target_units,
    cancellation_rate_pct,
    avg_contract_price,
    avg_price_per_sqft,
    avg_days_to_close,
    avg_gross_margin_pct,
    margin_target_pct * 100                                             AS margin_target_pct,
    target_attainment_pct,

    -- ── Cortex COMPLETE: Executive Summary ─────────────────────────
    SNOWFLAKE.CORTEX.COMPLETE(
        'mistral-7b',
        CONCAT(
            'You are a concise business analyst writing for a VP of Sales. ',
            'Write a 3-sentence performance summary for the ', region, ' region. ',
            'Regional Manager: ', regional_manager, '. ',
            'Closed units: ', closed_units::STRING, ' of ', sales_target_units::STRING,
            ' annual target (', target_attainment_pct::STRING, '% attainment). ',
            'Avg days to close: ', avg_days_to_close::STRING, ' days. ',
            'Avg price per sqft: $', avg_price_per_sqft::STRING, '. ',
            'Cancellation rate: ', cancellation_rate_pct::STRING, '%. ',
            'Avg gross margin: ', avg_gross_margin_pct::STRING, '% vs target of ',
            (margin_target_pct * 100)::STRING, '%. ',
            'Pipeline (under contract): ', pipeline_units::STRING, ' units. ',
            'Keep it factual, use plain English, no bullet points. ',
            'Highlight the biggest strength and biggest risk.'
        )
    )                                                                   AS ai_executive_summary,

    -- ── Cortex COMPLETE: Recommended Actions ───────────────────────
    SNOWFLAKE.CORTEX.COMPLETE(
        'mistral-7b',
        CONCAT(
            'You are a sales operations advisor. Based on this data, recommend 2 specific ',
            'action items for the ', region, ' region sales team. ',
            'Closed units: ', closed_units::STRING, ' of ', sales_target_units::STRING, ' target. ',
            'Avg days to close: ', avg_days_to_close::STRING, ' days (industry benchmark ~90). ',
            'Cancellation rate: ', cancellation_rate_pct::STRING, '%. ',
            'Avg gross margin: ', avg_gross_margin_pct::STRING, '%. ',
            'Write exactly 2 short bullet points starting with an action verb. ',
            'Be specific and data-driven.'
        )
    )                                                                   AS ai_action_items,

    CURRENT_TIMESTAMP()                                                 AS generated_at

FROM regional_agg;

-- -------------------------------------------------------
-- Verify output
-- -------------------------------------------------------
SELECT
    region,
    regional_manager,
    closed_units,
    target_attainment_pct,
    LEFT(ai_executive_summary, 200) AS summary_preview
FROM ASSESSMENT.MARTS.CORTEX_REGIONAL_SUMMARIES;
