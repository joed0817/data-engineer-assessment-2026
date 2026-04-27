-- ============================================================
-- Model: stg_regional_manager_targets
-- Layer: Staging
-- Materialization: View
--
-- Purpose: Standardize the regional manager reference table.
-- Simple pass-through with type casting and trimming.
-- Note: revenue_target_est is intentionally excluded here —
-- it is computed in the mart layer using actual avg closing
-- prices rather than a hardcoded constant.
-- ============================================================

WITH source AS (

    SELECT * FROM {{ source('raw', 'regional_manager_targets') }}

),

cleaned AS (

    SELECT
        TRIM(REGION)                                AS region,
        TRIM(REGIONAL_MANAGER)                      AS regional_manager,
        SALES_TARGET_UNITS                          AS sales_target_units,
        MARGIN_TARGET_PCT                           AS margin_target_pct

    FROM source

)

SELECT * FROM cleaned
