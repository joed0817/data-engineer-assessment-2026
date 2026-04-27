-- ============================================================
-- Model: mart_sales_performance
-- Layer: Marts
-- Materialization: Table
--
-- Purpose: The primary analysis-ready model. Joins enriched
-- sales data with regional targets, calculates all KPIs used
-- in the dashboard, and exposes one row per contract with full
-- context for slicing by region, community, consultant, time,
-- and plan. This is the single source of truth for the Streamlit
-- dashboard and Cortex AI functions.
-- ============================================================

WITH sales AS (

    SELECT * FROM {{ ref('stg_homebuilder_sales') }}

),

regions AS (

    SELECT * FROM {{ ref('stg_regional_manager_targets') }}

),

joined AS (

    SELECT
        -- ── Identity ───────────────────────────────────────────
        s.contract_id,

        -- ── Geography ──────────────────────────────────────────
        s.community,
        s.city,
        s.region,
        r.regional_manager,

        -- ── Product ────────────────────────────────────────────
        s.plan_name,
        s.sqft,
        s.bedrooms,
        s.bathrooms,

        -- ── Financials ─────────────────────────────────────────
        s.base_price,
        s.upgrade_amount,
        s.incentive_amount,
        s.contract_price,
        s.agent_commission,

        -- Key metric: price per square foot
        ROUND(s.contract_price / NULLIF(s.sqft, 0), 2)             AS price_per_sqft,

        -- Estimated gross margin (contract price minus base cost proxy)
        -- Using base_price as cost proxy since COGS not provided
        ROUND((s.contract_price - s.base_price) / NULLIF(s.contract_price, 0), 4)
                                                                    AS gross_margin_pct,

        -- Margin vs target: positive = above target, negative = below
        ROUND(
            ((s.contract_price - s.base_price) / NULLIF(s.contract_price, 0))
            - r.margin_target_pct,
            4
        )                                                           AS margin_vs_target,

        s.upgrade_attach_rate,
        s.incentive_rate,

        -- ── Time ───────────────────────────────────────────────
        s.contract_date,
        s.close_date,
        s.contract_year,
        s.contract_month,
        s.contract_month_name,
        s.contract_month_start,

        -- ── Velocity ───────────────────────────────────────────
        s.days_to_close_calc                                        AS days_to_close,

        -- Bucket for velocity analysis
        CASE
            WHEN s.days_to_close_calc <= 90  THEN 'Fast (≤90 days)'
            WHEN s.days_to_close_calc <= 120 THEN 'On-Track (91–120)'
            WHEN s.days_to_close_calc <= 150 THEN 'Slow (121–150)'
            WHEN s.days_to_close_calc > 150  THEN 'At-Risk (>150 days)'
            ELSE 'N/A'
        END                                                         AS close_speed_bucket,

        -- ── Status & Flags ─────────────────────────────────────
        s.is_closed,
        s.is_cancelled,
        s.is_under_contract,

        -- ── Lead Source ────────────────────────────────────────
        s.buyer_source,
        s.loan_type,
        s.is_referral,

        -- ── Sales Team ─────────────────────────────────────────
        s.sales_consultant,

        -- ── Targets (carried for per-row context) ──────────────
        r.sales_target_units,
        r.margin_target_pct
        -- Note: revenue_target_est is computed in mart_community_summary
        -- using actual avg closing price per community, not a hardcoded constant.

    FROM sales s
    LEFT JOIN regions r
        ON s.region = r.region

)

SELECT * FROM joined
