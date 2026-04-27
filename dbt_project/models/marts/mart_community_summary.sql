-- ============================================================
-- Model: mart_community_summary
-- Layer: Marts
-- Materialization: Table
--
-- Purpose: Community-level rollup for the dashboard scorecard.
-- Pre-aggregates KPIs so Streamlit renders instantly without
-- scanning the full transaction table on every filter change.
-- ============================================================

WITH base AS (

    SELECT * FROM {{ ref('mart_sales_performance') }}

),

summary AS (

    SELECT
        community,
        city,
        region,
        regional_manager,
        sales_target_units,
        margin_target_pct,

        -- ── Volume ─────────────────────────────────────────────
        COUNT(*)                                                    AS total_contracts,
        SUM(CASE WHEN is_closed        THEN 1 ELSE 0 END)          AS closed_units,
        SUM(CASE WHEN is_cancelled     THEN 1 ELSE 0 END)          AS cancelled_units,
        SUM(CASE WHEN is_under_contract THEN 1 ELSE 0 END)         AS under_contract_units,

        -- Cancellation rate (of all non-open contracts)
        ROUND(
            SUM(CASE WHEN is_cancelled THEN 1 ELSE 0 END)
            / NULLIF(SUM(CASE WHEN is_closed OR is_cancelled THEN 1 ELSE 0 END), 0),
            4
        )                                                           AS cancellation_rate,

        -- ── Revenue ────────────────────────────────────────────
        SUM(CASE WHEN is_closed THEN contract_price ELSE 0 END)     AS total_closed_revenue,
        AVG(CASE WHEN is_closed THEN contract_price ELSE NULL END)  AS avg_contract_price,
        AVG(CASE WHEN is_closed THEN price_per_sqft ELSE NULL END)  AS avg_price_per_sqft,

        -- Revenue target derived from actual avg closing price for this community
        -- (not a hardcoded constant — reflects real price mix per community)
        ROUND(
            sales_target_units
            * AVG(CASE WHEN is_closed THEN contract_price ELSE NULL END),
            0
        )                                                           AS revenue_target_est,

        -- ── Upgrades ───────────────────────────────────────────
        SUM(CASE WHEN is_closed THEN upgrade_amount  ELSE 0 END)    AS total_upgrade_revenue,
        AVG(CASE WHEN is_closed THEN upgrade_amount  ELSE NULL END) AS avg_upgrade_amount,
        AVG(CASE WHEN is_closed THEN upgrade_attach_rate ELSE NULL END) AS avg_upgrade_attach_rate,
        AVG(CASE WHEN is_closed THEN incentive_rate  ELSE NULL END) AS avg_incentive_rate,
        ROUND(
            SUM(CASE WHEN is_closed AND upgrade_amount > 0 THEN 1 ELSE 0 END)
            / NULLIF(SUM(CASE WHEN is_closed THEN 1 ELSE 0 END), 0),
            4
        )                                                           AS upgrade_attach_rate,
        ROUND(
            SUM(CASE WHEN is_closed THEN upgrade_amount ELSE 0 END)
            / NULLIF(SUM(CASE WHEN is_closed THEN contract_price ELSE 0 END), 0),
            4
        )                                                           AS upgrade_pct_of_revenue,

        -- ── Velocity ───────────────────────────────────────────
        AVG(CASE WHEN is_closed THEN days_to_close ELSE NULL END)   AS avg_days_to_close,
        MIN(CASE WHEN is_closed THEN days_to_close ELSE NULL END)   AS min_days_to_close,
        MAX(CASE WHEN is_closed THEN days_to_close ELSE NULL END)   AS max_days_to_close,

        -- ── Margin ─────────────────────────────────────────────
        AVG(CASE WHEN is_closed THEN gross_margin_pct ELSE NULL END) AS avg_gross_margin_pct,
        AVG(CASE WHEN is_closed THEN margin_vs_target ELSE NULL END) AS avg_margin_vs_target,

        -- ── Agent Commissions ──────────────────────────────────
        SUM(CASE WHEN is_closed THEN agent_commission ELSE 0 END)   AS total_commissions,

        -- ── Lead Sources (top source by volume) ────────────────
        MODE(buyer_source)                                          AS top_buyer_source,

        -- ── Date Range ─────────────────────────────────────────
        MIN(contract_date)                                          AS first_contract_date,
        MAX(contract_date)                                          AS latest_contract_date

    FROM base
    GROUP BY 1, 2, 3, 4, 5, 6

),

with_target_attainment AS (

    SELECT
        *,

        -- Pct of annual unit target achieved (closed only)
        ROUND(closed_units / NULLIF(sales_target_units, 0), 4)     AS target_attainment_pct,

        -- Performance tier
        CASE
            WHEN closed_units / NULLIF(sales_target_units, 0) >= 1.0  THEN 'Target Met'
            WHEN closed_units / NULLIF(sales_target_units, 0) >= 0.75 THEN 'On Track'
            WHEN closed_units / NULLIF(sales_target_units, 0) >= 0.50 THEN 'At Risk'
            ELSE 'Below Target'
        END                                                         AS performance_tier

    FROM summary

)

SELECT * FROM with_target_attainment
ORDER BY region, community
