-- ============================================================
-- Model: mart_consultant_performance
-- Layer: Marts
-- Materialization: Table
--
-- Purpose: Sales consultant leaderboard model. Used by the
-- dashboard to compare consultant metrics across volume,
-- revenue, velocity, and cancellation rate.
-- ============================================================

WITH base AS (

    SELECT * FROM {{ ref('mart_sales_performance') }}

)

SELECT
    sales_consultant,
    region,
    regional_manager,

    -- ── Volume ─────────────────────────────────────────────
    COUNT(*)                                                        AS total_contracts,
    SUM(CASE WHEN is_closed         THEN 1 ELSE 0 END)             AS closed_units,
    SUM(CASE WHEN is_cancelled      THEN 1 ELSE 0 END)             AS cancelled_units,
    SUM(CASE WHEN is_under_contract THEN 1 ELSE 0 END)             AS pipeline_units,

    -- Cancellation rate
    ROUND(
        SUM(CASE WHEN is_cancelled THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN is_closed OR is_cancelled THEN 1 ELSE 0 END), 0),
        4
    )                                                               AS cancellation_rate,

    -- ── Revenue ────────────────────────────────────────────
    SUM(CASE WHEN is_closed THEN contract_price   ELSE 0 END)      AS total_closed_revenue,
    AVG(CASE WHEN is_closed THEN contract_price   ELSE NULL END)   AS avg_sale_price,
    AVG(CASE WHEN is_closed THEN price_per_sqft   ELSE NULL END)   AS avg_price_per_sqft,
    SUM(CASE WHEN is_closed THEN agent_commission ELSE 0 END)      AS total_commissions,

    -- ── Upgrades ───────────────────────────────────────────
    AVG(CASE WHEN is_closed THEN upgrade_attach_rate ELSE NULL END) AS avg_upgrade_attach_rate,
    SUM(CASE WHEN is_closed THEN upgrade_amount      ELSE 0 END)   AS total_upgrade_revenue,

    -- ── Velocity ───────────────────────────────────────────
    AVG(CASE WHEN is_closed THEN days_to_close ELSE NULL END)      AS avg_days_to_close,

    -- ── Referrals ──────────────────────────────────────────
    SUM(CASE WHEN is_referral AND is_closed THEN 1 ELSE 0 END)     AS referral_closings,
    ROUND(
        SUM(CASE WHEN is_referral AND is_closed THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN is_closed THEN 1 ELSE 0 END), 0),
        4
    )                                                               AS referral_close_rate,

    -- ── Communities Worked ─────────────────────────────────
    COUNT(DISTINCT community)                                       AS communities_worked,

    -- ── Date Range ─────────────────────────────────────────
    MIN(contract_date)                                              AS first_contract_date,
    MAX(contract_date)                                              AS latest_contract_date

FROM base
GROUP BY 1, 2, 3
ORDER BY closed_units DESC
