"""
Data Engineer Assessment
Streamlit Dashboard 
Author: [Jose De La Cruz]
"""

import streamlit as st
import snowflake.connector
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import anthropic
from datetime import datetime, date
import warnings
warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Homebuilder Enterprises | Sales Intelligence",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────
# CUSTOM CSS
# ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: #f8f9fa;
        border-left: 4px solid #1f77b4;
        padding: 16px 20px;
        border-radius: 6px;
        margin-bottom: 12px;
    }
    .metric-card.green { border-left-color: #2ecc71; }
    .metric-card.red   { border-left-color: #e74c3c; }
    .metric-card.amber { border-left-color: #f39c12; }
    .ai-card {
        background: linear-gradient(135deg, #667eea22, #764ba222);
        border: 1px solid #667eea44;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #2c3e50;
        margin: 24px 0 12px 0;
        padding-bottom: 6px;
        border-bottom: 2px solid #ecf0f1;
    }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# SNOWFLAKE CONNECTION
# ──────────────────────────────────────────────────────────────
@st.cache_resource
def get_snowflake_conn():
    return snowflake.connector.connect(
        account=st.secrets["SNOWFLAKE_ACCOUNT"],
        user=st.secrets["SNOWFLAKE_USER"],
        password=st.secrets["SNOWFLAKE_PASSWORD"],
        warehouse="COMPUTE_WH",
        database="ASSESSMENT",
        schema="MARTS",
        role="SYSADMIN",
    )

@st.cache_data(ttl=300)
def query(_conn, sql: str) -> pd.DataFrame:
    return pd.read_sql(sql, _conn)

# ──────────────────────────────────────────────────────────────
# LOAD DATA
# ──────────────────────────────────────────────────────────────
try:
    conn = get_snowflake_conn()

    df_sales = query(conn, """
        SELECT * FROM ASSESSMENT.MARTS.MART_SALES_PERFORMANCE
    """)
    df_community = query(conn, """
        SELECT * FROM ASSESSMENT.MARTS.MART_COMMUNITY_SUMMARY
    """)
    df_consultant = query(conn, """
        SELECT * FROM ASSESSMENT.MARTS.MART_CONSULTANT_PERFORMANCE
    """)
    df_cortex = query(conn, """
        SELECT * FROM ASSESSMENT.MARTS.CORTEX_REGIONAL_SUMMARIES
    """)

    # Normalize column names to lowercase
    for df in [df_sales, df_community, df_consultant, df_cortex]:
        df.columns = [c.lower() for c in df.columns]

    # Parse dates
    df_sales["contract_date"] = pd.to_datetime(df_sales["contract_date"])
    df_sales["close_date"]    = pd.to_datetime(df_sales["close_date"], errors="coerce")

    LOAD_ERROR = None

except Exception as e:
    LOAD_ERROR = str(e)
    df_sales = df_community = df_consultant = df_cortex = pd.DataFrame()

# ──────────────────────────────────────────────────────────────
# SIDEBAR FILTERS
# ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/home.png", width=60)
    st.title("Homebuilder Enterprises")
    st.caption("Sales Intelligence Dashboard")
    st.divider()

    st.subheader("🔍 Filters")

    if not df_sales.empty:
        all_regions = sorted(df_sales["region"].dropna().unique().tolist())
        selected_regions = st.multiselect(
            "Region", all_regions, default=all_regions
        )

        all_communities = sorted(df_sales[df_sales["region"].isin(selected_regions)]["community"].unique().tolist())
        selected_communities = st.multiselect(
            "Community", all_communities, default=all_communities
        )

        all_consultants = sorted(df_sales["sales_consultant"].dropna().unique().tolist())
        selected_consultants = st.multiselect(
            "Sales Consultant", all_consultants, default=all_consultants
        )

        date_min = df_sales["contract_date"].min().date()
        date_max = df_sales["contract_date"].max().date()
        date_range = st.date_input(
            "Contract Date Range",
            value=(date_min, date_max),
            min_value=date_min,
            max_value=date_max,
        )

        status_options = ["Closed", "Cancelled", "Under Contract"]
        selected_statuses = st.multiselect(
            "Contract Status", status_options, default=status_options
        )

        # Apply filters
        filt = (
            df_sales["region"].isin(selected_regions) &
            df_sales["community"].isin(selected_communities) &
            df_sales["sales_consultant"].isin(selected_consultants) &
            (df_sales["contract_date"].dt.date >= date_range[0]) &
            (df_sales["contract_date"].dt.date <= date_range[1]) &
            (
                (df_sales["is_closed"]         & ("Closed"         in selected_statuses)) |
                (df_sales["is_cancelled"]      & ("Cancelled"      in selected_statuses)) |
                (df_sales["is_under_contract"] & ("Under Contract" in selected_statuses))
            )
        )
        df_f = df_sales[filt].copy()
    else:
        df_f = pd.DataFrame()

    st.divider()
    st.caption(f"Data through {date_max.strftime('%B %Y') if not df_sales.empty else 'N/A'}")

# ──────────────────────────────────────────────────────────────
# MAIN CONTENT — TABS
# ──────────────────────────────────────────────────────────────
if LOAD_ERROR:
    st.error(f"⚠️ Could not connect to Snowflake: {LOAD_ERROR}")
    st.info("Check your Streamlit secrets configuration.")
    st.stop()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Executive Overview",
    "🏘️ Community Analysis",
    "👤 Consultant Leaderboard",
    "💰 Upgrade Revenue",
    "🤖 AI Insights",
    "💬 Ask the Data",
])

# ══════════════════════════════════════════════════════════════
# TAB 1 — EXECUTIVE OVERVIEW
# ══════════════════════════════════════════════════════════════
with tab1:
    st.header("Executive Overview")

    if df_f.empty:
        st.warning("No data matches your current filters.")
    else:
        closed = df_f[df_f["is_closed"] == True]
        cancelled = df_f[df_f["is_cancelled"] == True]

        # ── KPI Row ────────────────────────────────────────────
        k1, k2, k3, k4, k5 = st.columns(5)

        total_target = df_f["sales_target_units"].fillna(0).pipe(
            lambda s: df_f.drop_duplicates("region")[["region","sales_target_units"]]["sales_target_units"].sum()
        )

        k1.metric("Closed Units",     f"{len(closed):,}",
                  help="Contracts that reached closing")
        k2.metric("Total Revenue",    f"${closed['contract_price'].sum()/1e6:.1f}M",
                  help="Sum of all closed contract prices")
        k3.metric("Avg Price / Sqft", f"${closed['price_per_sqft'].mean():.0f}",
                  help="Average across closed contracts")
        k4.metric("Avg Days to Close",f"{closed['days_to_close'].mean():.0f}",
                  help="Average calendar days from contract to close")
        k5.metric("Cancellation Rate",
                  f"{len(cancelled)/max(len(closed)+len(cancelled),1)*100:.1f}%",
                  help="Cancelled ÷ (Closed + Cancelled)")

        st.divider()

        # ── Monthly Volume Trend ────────────────────────────────
        st.markdown('<div class="section-header">Monthly Contract Volume & Revenue</div>', unsafe_allow_html=True)

        monthly = (
            df_f.assign(month=df_f["contract_date"].dt.to_period("M").dt.to_timestamp())
            .groupby(["month","is_closed","is_cancelled"])
            .size().reset_index(name="count")
        )
        monthly_closed = (
            closed.assign(month=closed["contract_date"].dt.to_period("M").dt.to_timestamp())
            .groupby("month")["contract_price"].sum().reset_index()
        )
        monthly_vol = (
            df_f.assign(month=df_f["contract_date"].dt.to_period("M").dt.to_timestamp())
            .groupby(["month","is_closed"])
            .size().reset_index(name="count")
        )

        fig_trend = make_subplots(specs=[[{"secondary_y": True}]])
        closed_monthly = monthly_vol[monthly_vol["is_closed"] == True]
        open_monthly   = monthly_vol[monthly_vol["is_closed"] == False]

        fig_trend.add_trace(go.Bar(
            x=closed_monthly["month"], y=closed_monthly["count"],
            name="Closed", marker_color="#2ecc71", opacity=0.85
        ), secondary_y=False)
        fig_trend.add_trace(go.Bar(
            x=open_monthly["month"], y=open_monthly["count"],
            name="Not Closed", marker_color="#95a5a6", opacity=0.6
        ), secondary_y=False)
        fig_trend.add_trace(go.Scatter(
            x=monthly_closed["month"], y=monthly_closed["contract_price"]/1e6,
            name="Revenue ($M)", mode="lines+markers",
            line=dict(color="#e74c3c", width=2), marker=dict(size=6)
        ), secondary_y=True)

        fig_trend.update_layout(
            barmode="stack", height=380, margin=dict(t=20),
            legend=dict(orientation="h", y=1.05),
        )
        fig_trend.update_yaxes(title_text="Units", secondary_y=False)
        fig_trend.update_yaxes(title_text="Revenue ($M)", secondary_y=True)
        st.plotly_chart(fig_trend, use_container_width=True)

        col_l, col_r = st.columns(2)

        # ── Price/Sqft by Region ────────────────────────────────
        with col_l:
            st.markdown('<div class="section-header">Price per Sqft by Region</div>', unsafe_allow_html=True)
            region_price = (
                closed.groupby("region")["price_per_sqft"]
                .agg(["mean","median","std"]).reset_index()
                .sort_values("mean", ascending=False)
            )
            fig_box = px.box(
                closed, x="region", y="price_per_sqft", color="region",
                color_discrete_sequence=px.colors.qualitative.Set2,
                labels={"price_per_sqft": "$/sqft", "region": ""},
                height=340,
            )
            fig_box.update_layout(showlegend=False, margin=dict(t=10))
            st.plotly_chart(fig_box, use_container_width=True)

        # ── Loan Type Mix ───────────────────────────────────────
        with col_r:
            st.markdown('<div class="section-header">Financing Mix (Closed Contracts)</div>', unsafe_allow_html=True)
            loan_mix = closed["loan_type"].value_counts().reset_index()
            loan_mix.columns = ["loan_type", "count"]
            fig_pie = px.pie(
                loan_mix, names="loan_type", values="count",
                color_discrete_sequence=px.colors.qualitative.Set3,
                hole=0.45, height=340,
            )
            fig_pie.update_traces(textposition="outside", textinfo="percent+label")
            fig_pie.update_layout(showlegend=False, margin=dict(t=10))
            st.plotly_chart(fig_pie, use_container_width=True)

        # ── Lead Source Funnel ──────────────────────────────────
        st.markdown('<div class="section-header">Lead Source Performance</div>', unsafe_allow_html=True)
        source_perf = (
            df_f.groupby("buyer_source").agg(
                total=("contract_id", "count"),
                closed=("is_closed", "sum"),
            ).reset_index()
        )
        source_perf["close_rate"] = source_perf["closed"] / source_perf["total"] * 100
        source_perf = source_perf.sort_values("closed", ascending=True)

        fig_source = go.Figure()
        fig_source.add_trace(go.Bar(
            y=source_perf["buyer_source"], x=source_perf["total"],
            name="Total Contracts", orientation="h",
            marker_color="#bdc3c7", opacity=0.7
        ))
        fig_source.add_trace(go.Bar(
            y=source_perf["buyer_source"], x=source_perf["closed"],
            name="Closed", orientation="h",
            marker_color="#2980b9", opacity=0.9
        ))
        fig_source.update_layout(
            barmode="overlay", height=350, margin=dict(t=10),
            xaxis_title="Contracts", yaxis_title="",
            legend=dict(orientation="h", y=1.05),
        )
        st.plotly_chart(fig_source, use_container_width=True)

# ══════════════════════════════════════════════════════════════
# TAB 2 — COMMUNITY ANALYSIS
# ══════════════════════════════════════════════════════════════
with tab2:
    st.header("Community Analysis")

    df_comm_f = df_community[df_community["region"].isin(selected_regions)].copy()
    df_comm_f.columns = [c.lower() for c in df_comm_f.columns]

    if df_comm_f.empty:
        st.warning("No community data for selected filters.")
    else:
        # ── Community Scorecard ─────────────────────────────────
        st.markdown('<div class="section-header">Community Scorecard</div>', unsafe_allow_html=True)

        def tier_color(tier):
            return {"Target Met": "🟢", "On Track": "🟡", "At Risk": "🟠", "Below Target": "🔴"}.get(tier, "⚪")

        display_cols = [
            "community", "region", "regional_manager",
            "closed_units", "sales_target_units", "target_attainment_pct",
            "cancellation_rate", "avg_price_per_sqft", "avg_days_to_close",
            "avg_gross_margin_pct", "performance_tier"
        ]
        scorecard = df_comm_f[display_cols].copy()
        scorecard["target_attainment_pct"] = (scorecard["target_attainment_pct"] * 100).round(1).astype(str) + "%"
        scorecard["cancellation_rate"]     = (scorecard["cancellation_rate"] * 100).round(1).astype(str) + "%"
        scorecard["avg_price_per_sqft"]    = "$" + scorecard["avg_price_per_sqft"].round(2).astype(str)
        scorecard["avg_days_to_close"]     = scorecard["avg_days_to_close"].round(0).astype(str) + " days"
        scorecard["avg_gross_margin_pct"]  = (scorecard["avg_gross_margin_pct"] * 100).round(1).astype(str) + "%"
        scorecard["performance_tier"]      = scorecard["performance_tier"].apply(lambda x: tier_color(x) + " " + x)
        scorecard.columns = [
            "Community", "Region", "Manager",
            "Closed", "Target", "Attainment",
            "Cancel Rate", "$/Sqft", "Avg Days",
            "Margin", "Status"
        ]
        st.dataframe(scorecard, use_container_width=True, hide_index=True)

        col_l, col_r = st.columns(2)

        # ── Closed Units vs Target ──────────────────────────────
        with col_l:
            st.markdown('<div class="section-header">Closed Units vs Target by Community</div>', unsafe_allow_html=True)
            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(
                name="Target", x=df_comm_f["community"],
                y=df_comm_f["sales_target_units"],
                marker_color="#ecf0f1", marker_line_color="#bdc3c7",
                marker_line_width=1, opacity=0.8
            ))
            fig_bar.add_trace(go.Bar(
                name="Closed", x=df_comm_f["community"],
                y=df_comm_f["closed_units"],
                marker_color="#27ae60", opacity=0.9
            ))
            fig_bar.update_layout(
                barmode="overlay", height=360, margin=dict(t=10),
                xaxis_tickangle=-30, yaxis_title="Units"
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        # ── Cancellation Rate ───────────────────────────────────
        with col_r:
            st.markdown('<div class="section-header">Cancellation Rate by Community</div>', unsafe_allow_html=True)
            cancel_df = df_comm_f.sort_values("cancellation_rate", ascending=True)
            colors = ["#e74c3c" if r > 0.1 else "#f39c12" if r > 0.06 else "#27ae60"
                      for r in cancel_df["cancellation_rate"]]
            fig_cancel = go.Figure(go.Bar(
                x=cancel_df["cancellation_rate"] * 100,
                y=cancel_df["community"],
                orientation="h",
                marker_color=colors,
                text=(cancel_df["cancellation_rate"] * 100).round(1).astype(str) + "%",
                textposition="outside",
            ))
            fig_cancel.update_layout(
                height=360, margin=dict(t=10),
                xaxis_title="Cancellation Rate (%)", yaxis_title=""
            )
            st.plotly_chart(fig_cancel, use_container_width=True)

        # ── Price/Sqft vs Days to Close Scatter ─────────────────
        st.markdown('<div class="section-header">Price Efficiency vs Close Speed</div>', unsafe_allow_html=True)
        st.caption("Bubble size = closed units | Ideal quadrant: upper-left (high $/sqft, fast close)")
        fig_scatter = px.scatter(
            df_comm_f,
            x="avg_days_to_close", y="avg_price_per_sqft",
            size="closed_units", color="region",
            text="community", hover_data=["regional_manager","closed_units"],
            labels={
                "avg_days_to_close": "Avg Days to Close",
                "avg_price_per_sqft": "Avg Price / Sqft ($)",
            },
            color_discrete_sequence=px.colors.qualitative.Set1,
            height=420,
        )
        fig_scatter.update_traces(textposition="top center", textfont_size=10)
        fig_scatter.update_layout(margin=dict(t=10))
        st.plotly_chart(fig_scatter, use_container_width=True)

# ══════════════════════════════════════════════════════════════
# TAB 3 — CONSULTANT LEADERBOARD
# ══════════════════════════════════════════════════════════════
with tab3:
    st.header("Consultant Leaderboard")

    df_con_f = df_consultant[df_consultant["sales_consultant"].isin(selected_consultants)].copy()
    df_con_f.columns = [c.lower() for c in df_con_f.columns]

    if df_con_f.empty:
        st.warning("No consultant data for selected filters.")
    else:
        # ── Leaderboard Table ───────────────────────────────────
        st.markdown('<div class="section-header">Performance Rankings</div>', unsafe_allow_html=True)
        lb = df_con_f[[
            "sales_consultant","region","closed_units","total_closed_revenue",
            "avg_sale_price","avg_price_per_sqft","avg_days_to_close",
            "cancellation_rate","avg_upgrade_attach_rate","total_commissions"
        ]].sort_values("closed_units", ascending=False).copy()
        lb["rank"] = range(1, len(lb)+1)
        lb["medal"] = lb["rank"].map({1:"🥇",2:"🥈",3:"🥉"}).fillna(lb["rank"].astype(str))
        lb["total_closed_revenue"]    = lb["total_closed_revenue"].apply(lambda x: f"${x:,.0f}")
        lb["avg_sale_price"]          = lb["avg_sale_price"].apply(lambda x: f"${x:,.0f}")
        lb["avg_price_per_sqft"]      = lb["avg_price_per_sqft"].apply(lambda x: f"${x:.2f}")
        lb["avg_days_to_close"]       = lb["avg_days_to_close"].apply(lambda x: f"{x:.0f}")
        lb["cancellation_rate"]       = (lb["cancellation_rate"] * 100).round(1).astype(str) + "%"
        lb["avg_upgrade_attach_rate"] = (lb["avg_upgrade_attach_rate"] * 100).round(1).astype(str) + "%"
        lb["total_commissions"]       = lb["total_commissions"].apply(lambda x: f"${x:,.0f}")
        lb = lb[["medal","sales_consultant","region","closed_units","total_closed_revenue",
                  "avg_sale_price","avg_price_per_sqft","avg_days_to_close",
                  "cancellation_rate","avg_upgrade_attach_rate","total_commissions"]]
        lb.columns = ["#","Consultant","Region","Closed","Revenue","Avg Price",
                      "$/Sqft","Days","Cancel %","Upgrade %","Commissions"]
        st.dataframe(lb, use_container_width=True, hide_index=True)

        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown('<div class="section-header">Closed Units by Consultant</div>', unsafe_allow_html=True)
            cons_sorted = df_con_f.sort_values("closed_units", ascending=True)
            fig_cons = px.bar(
                cons_sorted, x="closed_units", y="sales_consultant",
                color="region", orientation="h", height=320,
                color_discrete_sequence=px.colors.qualitative.Set2,
                labels={"closed_units":"Closed Units","sales_consultant":""},
            )
            fig_cons.update_layout(margin=dict(t=10), showlegend=True)
            st.plotly_chart(fig_cons, use_container_width=True)

        with col_r:
            st.markdown('<div class="section-header">Avg Days to Close by Consultant</div>', unsafe_allow_html=True)
            sorted_speed = df_con_f.sort_values("avg_days_to_close")
            colors_speed = ["#27ae60" if d <= 100 else "#f39c12" if d <= 130 else "#e74c3c"
                            for d in sorted_speed["avg_days_to_close"]]
            fig_speed = go.Figure(go.Bar(
                x=sorted_speed["sales_consultant"],
                y=sorted_speed["avg_days_to_close"],
                marker_color=colors_speed,
                text=sorted_speed["avg_days_to_close"].round(0),
                textposition="outside",
            ))
            fig_speed.add_hline(y=126, line_dash="dash", line_color="gray",
                                annotation_text="Dataset Avg (126d)")
            fig_speed.update_layout(
                height=320, margin=dict(t=10),
                yaxis_title="Avg Days to Close",
            )
            st.plotly_chart(fig_speed, use_container_width=True)

        # ── Upgrade Attach Rate vs Revenue ──────────────────────
        st.markdown('<div class="section-header">Upgrade Attach Rate vs Total Revenue</div>', unsafe_allow_html=True)
        fig_upg = px.scatter(
            df_con_f,
            x="avg_upgrade_attach_rate", y="total_closed_revenue",
            size="closed_units", color="sales_consultant", text="sales_consultant",
            labels={
                "avg_upgrade_attach_rate": "Avg Upgrade Attach Rate",
                "total_closed_revenue": "Total Closed Revenue ($)",
            },
            height=380,
        )
        fig_upg.update_traces(textposition="top center")
        fig_upg.update_layout(margin=dict(t=10), showlegend=False)
        st.plotly_chart(fig_upg, use_container_width=True)

# ══════════════════════════════════════════════════════════════
# TAB 4 — UPGRADE REVENUE ANALYSIS
# ══════════════════════════════════════════════════════════════
with tab4:
    st.header("Upgrade Revenue Analysis")
    st.caption("Analyzing upgrade attach rates and revenue contribution across plans, communities, consultants, and regions.")

    if df_f.empty:
        st.warning("No data matches your current filters.")
    else:
        closed = df_f[df_f["is_closed"] == True].copy()

        if closed.empty:
            st.warning("No closed contracts in the current filter selection.")
        else:
            # ── KPI Row ────────────────────────────────────────────
            total_upgrade_rev   = closed["upgrade_amount"].sum()
            total_contract_rev  = closed["contract_price"].sum()
            avg_upgrade         = closed["upgrade_amount"].mean()
            attach_rate         = (closed["upgrade_amount"] > 0).mean() * 100
            upgrade_pct_rev     = total_upgrade_rev / total_contract_rev * 100 if total_contract_rev > 0 else 0

            u1, u2, u3, u4 = st.columns(4)
            u1.metric("Total Upgrade Revenue",  f"${total_upgrade_rev:,.0f}",
                      help="Sum of all upgrade amounts on closed contracts")
            u2.metric("Avg Upgrade per Home",   f"${avg_upgrade:,.0f}",
                      help="Average upgrade dollar value per closed contract")
            u3.metric("Upgrade Attach Rate",    f"{attach_rate:.1f}%",
                      help="% of closed contracts with at least one upgrade")
            u4.metric("Upgrades as % of Revenue", f"{upgrade_pct_rev:.1f}%",
                      help="Total upgrade revenue ÷ total contract revenue")

            st.divider()

            # ── Row 1: By Plan & By Region ─────────────────────────
            col_l, col_r = st.columns(2)

            with col_l:
                st.markdown('<div class="section-header">Upgrade Revenue by Floor Plan</div>', unsafe_allow_html=True)
                plan_upg = (
                    closed.groupby("plan_name")
                    .agg(
                        total_upgrade=("upgrade_amount", "sum"),
                        avg_upgrade=("upgrade_amount", "mean"),
                        contracts=("contract_id", "count"),
                        attach_rate=("upgrade_amount", lambda x: (x > 0).mean() * 100),
                    )
                    .reset_index()
                    .sort_values("total_upgrade", ascending=True)
                )
                fig_plan = go.Figure()
                fig_plan.add_trace(go.Bar(
                    y=plan_upg["plan_name"],
                    x=plan_upg["total_upgrade"],
                    orientation="h",
                    marker_color="#7F77DD",
                    opacity=0.85,
                    text=plan_upg["total_upgrade"].apply(lambda x: f"${x:,.0f}"),
                    textposition="outside",
                    customdata=plan_upg[["avg_upgrade", "attach_rate", "contracts"]].values,
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "Total: $%{x:,.0f}<br>"
                        "Avg per home: $%{customdata[0]:,.0f}<br>"
                        "Attach rate: %{customdata[1]:.1f}%<br>"
                        "Contracts: %{customdata[2]}<extra></extra>"
                    ),
                ))
                fig_plan.update_layout(
                    height=340, margin=dict(t=10, r=80),
                    xaxis_title="Total Upgrade Revenue ($)",
                    yaxis_title="",
                    xaxis_tickformat="$,.0f",
                )
                st.plotly_chart(fig_plan, use_container_width=True)

            with col_r:
                st.markdown('<div class="section-header">Upgrade Revenue by Region</div>', unsafe_allow_html=True)
                region_upg = (
                    closed.groupby("region")
                    .agg(
                        total_upgrade=("upgrade_amount", "sum"),
                        avg_upgrade=("upgrade_amount", "mean"),
                        total_revenue=("contract_price", "sum"),
                        contracts=("contract_id", "count"),
                    )
                    .reset_index()
                )
                region_upg["upgrade_pct"] = region_upg["total_upgrade"] / region_upg["total_revenue"] * 100

                fig_region = go.Figure()
                fig_region.add_trace(go.Bar(
                    name="Upgrade Revenue",
                    x=region_upg["region"],
                    y=region_upg["total_upgrade"],
                    marker_color="#1D9E75",
                    opacity=0.85,
                    text=region_upg["total_upgrade"].apply(lambda x: f"${x/1e6:.2f}M"),
                    textposition="outside",
                ))
                fig_region.add_trace(go.Scatter(
                    name="Upgrades as % of Revenue",
                    x=region_upg["region"],
                    y=region_upg["upgrade_pct"],
                    mode="markers+text",
                    marker=dict(size=12, color="#D85A30", symbol="diamond"),
                    text=region_upg["upgrade_pct"].apply(lambda x: f"{x:.1f}%"),
                    textposition="top center",
                    yaxis="y2",
                ))
                fig_region.update_layout(
                    height=340, margin=dict(t=10),
                    yaxis=dict(title="Total Upgrade Revenue ($)", tickformat="$,.0f"),
                    yaxis2=dict(title="% of Contract Revenue", overlaying="y", side="right",
                                tickformat=".1f", ticksuffix="%"),
                    legend=dict(orientation="h", y=1.08),
                    barmode="group",
                )
                st.plotly_chart(fig_region, use_container_width=True)

            # ── Row 2: By Community ────────────────────────────────
            st.markdown('<div class="section-header">Upgrade Revenue Breakdown by Community</div>', unsafe_allow_html=True)

            comm_upg = (
                closed.groupby(["community", "region"])
                .agg(
                    total_upgrade=("upgrade_amount", "sum"),
                    avg_upgrade=("upgrade_amount", "mean"),
                    base_revenue=("base_price", "sum"),
                    contract_revenue=("contract_price", "sum"),
                    contracts=("contract_id", "count"),
                    attach_rate=("upgrade_amount", lambda x: (x > 0).mean() * 100),
                )
                .reset_index()
                .sort_values("total_upgrade", ascending=False)
            )
            comm_upg["upgrade_pct_of_rev"] = comm_upg["total_upgrade"] / comm_upg["contract_revenue"] * 100

            fig_comm = go.Figure()
            colors_by_region = {r: c for r, c in zip(
                comm_upg["region"].unique(),
                ["#7F77DD", "#1D9E75", "#D85A30"]
            )}
            for region, grp in comm_upg.groupby("region"):
                fig_comm.add_trace(go.Bar(
                    name=region,
                    x=grp["community"],
                    y=grp["total_upgrade"],
                    marker_color=colors_by_region.get(region, "#888"),
                    opacity=0.85,
                    customdata=grp[["avg_upgrade", "attach_rate", "contracts", "upgrade_pct_of_rev"]].values,
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        "Total upgrades: $%{y:,.0f}<br>"
                        "Avg per home: $%{customdata[0]:,.0f}<br>"
                        "Attach rate: %{customdata[1]:.1f}%<br>"
                        "Contracts: %{customdata[2]}<br>"
                        "% of revenue: %{customdata[3]:.1f}%<extra></extra>"
                    ),
                ))
            fig_comm.update_layout(
                height=360, margin=dict(t=10),
                xaxis_title="", yaxis_title="Total Upgrade Revenue ($)",
                yaxis_tickformat="$,.0f",
                xaxis_tickangle=-20,
                legend=dict(orientation="h", y=1.05),
                barmode="group",
            )
            st.plotly_chart(fig_comm, use_container_width=True)

            # ── Row 3: By Consultant & Distribution ───────────────
            col_l2, col_r2 = st.columns(2)

            with col_l2:
                st.markdown('<div class="section-header">Avg Upgrade per Home by Consultant</div>', unsafe_allow_html=True)
                cons_upg = (
                    closed.groupby("sales_consultant")
                    .agg(
                        avg_upgrade=("upgrade_amount", "mean"),
                        total_upgrade=("upgrade_amount", "sum"),
                        contracts=("contract_id", "count"),
                        attach_rate=("upgrade_amount", lambda x: (x > 0).mean() * 100),
                    )
                    .reset_index()
                    .sort_values("avg_upgrade", ascending=True)
                )
                overall_avg = closed["upgrade_amount"].mean()
                bar_colors = [
                    "#1D9E75" if v >= overall_avg else "#D85A30"
                    for v in cons_upg["avg_upgrade"]
                ]
                fig_cons_upg = go.Figure(go.Bar(
                    y=cons_upg["sales_consultant"],
                    x=cons_upg["avg_upgrade"],
                    orientation="h",
                    marker_color=bar_colors,
                    opacity=0.85,
                    text=cons_upg["avg_upgrade"].apply(lambda x: f"${x:,.0f}"),
                    textposition="outside",
                    customdata=cons_upg[["total_upgrade", "attach_rate", "contracts"]].values,
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "Avg upgrade: $%{x:,.0f}<br>"
                        "Total upgrade rev: $%{customdata[0]:,.0f}<br>"
                        "Attach rate: %{customdata[1]:.1f}%<br>"
                        "Contracts: %{customdata[2]}<extra></extra>"
                    ),
                ))
                fig_cons_upg.add_vline(
                    x=overall_avg, line_dash="dash", line_color="gray",
                    annotation_text=f"Avg ${overall_avg:,.0f}",
                    annotation_position="top right",
                )
                fig_cons_upg.update_layout(
                    height=320, margin=dict(t=10, r=70),
                    xaxis_title="Avg Upgrade Amount ($)",
                    yaxis_title="",
                    xaxis_tickformat="$,.0f",
                )
                st.plotly_chart(fig_cons_upg, use_container_width=True)
                st.caption("🟢 Above average  🔴 Below average")

            with col_r2:
                st.markdown('<div class="section-header">Upgrade Amount Distribution</div>', unsafe_allow_html=True)
                fig_hist = px.histogram(
                    closed,
                    x="upgrade_amount",
                    nbins=20,
                    color="region",
                    color_discrete_sequence=["#7F77DD", "#1D9E75", "#D85A30"],
                    labels={"upgrade_amount": "Upgrade Amount ($)", "count": "Contracts"},
                    barmode="overlay",
                    opacity=0.7,
                    height=320,
                )
                fig_hist.update_layout(
                    margin=dict(t=10),
                    xaxis_tickformat="$,.0f",
                    legend=dict(orientation="h", y=1.05),
                    yaxis_title="Number of Contracts",
                )
                st.plotly_chart(fig_hist, use_container_width=True)

            # ── Row 4: Upgrade vs Contract Price Scatter ───────────
            st.markdown('<div class="section-header">Upgrade Amount vs Contract Price — by Plan</div>', unsafe_allow_html=True)
            st.caption("Bubble size = sqft | Shows which plans drive the highest upgrade revenue relative to sale price")

            fig_scatter_upg = px.scatter(
                closed,
                x="contract_price",
                y="upgrade_amount",
                color="plan_name",
                size="sqft",
                hover_data=["community", "sales_consultant", "region", "upgrade_attach_rate"],
                color_discrete_sequence=px.colors.qualitative.Safe,
                labels={
                    "contract_price": "Contract Price ($)",
                    "upgrade_amount": "Upgrade Amount ($)",
                    "plan_name": "Plan",
                },
                height=420,
                opacity=0.75,
            )
            fig_scatter_upg.update_layout(
                margin=dict(t=10),
                xaxis_tickformat="$,.0f",
                yaxis_tickformat="$,.0f",
                legend=dict(orientation="h", y=1.05),
            )
            st.plotly_chart(fig_scatter_upg, use_container_width=True)

            # ── Row 5: Upgrade Revenue Detail Table ───────────────
            st.markdown('<div class="section-header">Upgrade Revenue Summary Table</div>', unsafe_allow_html=True)
            summary_tbl = (
                closed.groupby(["region", "community", "plan_name"])
                .agg(
                    contracts=("contract_id", "count"),
                    total_upgrade_rev=("upgrade_amount", "sum"),
                    avg_upgrade=("upgrade_amount", "mean"),
                    attach_rate=("upgrade_amount", lambda x: (x > 0).mean() * 100),
                    avg_contract_price=("contract_price", "mean"),
                )
                .reset_index()
                .sort_values("total_upgrade_rev", ascending=False)
            )
            summary_tbl["total_upgrade_rev"] = summary_tbl["total_upgrade_rev"].apply(lambda x: f"${x:,.0f}")
            summary_tbl["avg_upgrade"]        = summary_tbl["avg_upgrade"].apply(lambda x: f"${x:,.0f}")
            summary_tbl["attach_rate"]        = summary_tbl["attach_rate"].round(1).astype(str) + "%"
            summary_tbl["avg_contract_price"] = summary_tbl["avg_contract_price"].apply(lambda x: f"${x:,.0f}")
            summary_tbl.columns = ["Region", "Community", "Plan", "Contracts",
                                    "Total Upgrade Rev", "Avg Upgrade", "Attach Rate", "Avg Contract Price"]
            st.dataframe(summary_tbl, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════
# TAB 5 — AI INSIGHTS (Cortex)
# ══════════════════════════════════════════════════════════════
with tab5:
    st.header("🤖 AI-Generated Regional Insights")
    st.caption("Powered by Snowflake Cortex COMPLETE (mistral-7b) — summaries generated from live warehouse data.")

    if df_cortex.empty:
        st.warning("Cortex summaries not yet generated. Run `03_cortex_ai_summaries.sql` in Snowflake.")
    else:
        for _, row in df_cortex.iterrows():
            with st.expander(f"📍 {row['region']} — {row['regional_manager']}", expanded=True):
                m1, m2, m3, m4 = st.columns(4)
                attainment = float(row.get("target_attainment_pct", 0))
                m1.metric("Closed Units",   f"{int(row['closed_units'])} / {int(row['sales_target_units'])}")
                m2.metric("Attainment",     f"{attainment:.1f}%",
                          delta=f"{attainment-100:.1f}%" if attainment != 100 else None)
                m3.metric("Cancel Rate",    f"{float(row['cancellation_rate_pct']):.1f}%")
                m4.metric("Avg Days/Close", f"{float(row['avg_days_to_close']):.0f}")

                st.markdown("**Executive Summary**")
                st.markdown(f'<div class="ai-card">{row["ai_executive_summary"]}</div>',
                            unsafe_allow_html=True)
                st.markdown("**Recommended Actions**")
                st.markdown(f'<div class="ai-card">{row["ai_action_items"]}</div>',
                            unsafe_allow_html=True)

                generated = row.get("generated_at", "")
                if generated:
                    st.caption(f"Generated: {str(generated)[:19]}")

# ══════════════════════════════════════════════════════════════
# TAB 6 — NATURAL LANGUAGE QUERY
# ══════════════════════════════════════════════════════════════
with tab6:
    st.header("💬 Ask the Data")
    st.caption(
        "Ask plain-English questions about Homebuilder Enterprises sales performance. "
        "Powered by Claude (Anthropic) grounded in your live Snowflake data."
    )

    # ── Build Data Context ──────────────────────────────────────
    def build_data_context(df_sales, df_community, df_consultant):
        """
        Build a rich data context for Claude. Covers all major dimensions:
        overview, financials, upgrades, velocity, lead sources, financing,
        regional targets, community scorecard, and consultant leaderboard.
        Avoids sending 600 raw rows — uses pre-aggregated summaries instead.
        """
        ctx_parts = []

        if not df_sales.empty:
            closed   = df_sales[df_sales["is_closed"] == True]
            cancelled = df_sales[df_sales["is_cancelled"] == True]

            # ── 1. Dataset Overview ────────────────────────────────
            ctx_parts.append(f"""
DATASET OVERVIEW:
- Total contracts: {len(df_sales):,}
- Closed: {int(df_sales["is_closed"].sum())} | Cancelled: {int(df_sales["is_cancelled"].sum())} | Under Contract: {int(df_sales["is_under_contract"].sum())}
- Cancellation rate: {len(cancelled)/max(len(closed)+len(cancelled),1)*100:.1f}%
- Date range: {df_sales["contract_date"].min().date()} to {df_sales["contract_date"].max().date()}
- Regions: {", ".join(sorted(df_sales["region"].unique()))}
- Communities ({df_sales["community"].nunique()} total): {", ".join(sorted(df_sales["community"].unique()))}
- Sales consultants: {", ".join(sorted(df_sales["sales_consultant"].unique()))}
- Floor plans: {", ".join(sorted(df_sales["plan_name"].unique()))}
- Loan types available: {", ".join(sorted(df_sales["loan_type"].unique()))}
- Buyer sources: {", ".join(sorted(df_sales["buyer_source"].unique()))}
""")

            # ── 2. Financial Summary (closed only) ────────────────
            if not closed.empty:
                ctx_parts.append(f"""
FINANCIAL SUMMARY (closed contracts only):
- Total revenue: ${closed["contract_price"].sum():,.0f}
- Avg contract price: ${closed["contract_price"].mean():,.0f}
- Min contract price: ${closed["contract_price"].min():,.0f}
- Max contract price: ${closed["contract_price"].max():,.0f}
- Avg price per sqft: ${closed["price_per_sqft"].mean():.2f}
- Avg base price: ${closed["base_price"].mean():,.0f}
- Avg gross margin: {closed["gross_margin_pct"].mean()*100:.1f}%
- Total agent commissions paid: ${closed["agent_commission"].sum():,.0f}
- Avg agent commission: ${closed["agent_commission"].mean():,.0f}
""")

            # ── 3. Upgrade Revenue Summary ─────────────────────────
            if not closed.empty:
                upgrade_by_plan = (
                    closed.groupby("plan_name")["upgrade_amount"]
                    .agg(total="sum", avg="mean", count="count")
                    .sort_values("total", ascending=False)
                    .reset_index()
                )
                upgrade_by_region = (
                    closed.groupby("region")["upgrade_amount"]
                    .agg(total="sum", avg="mean")
                    .reset_index()
                )
                upgrade_by_consultant = (
                    closed.groupby("sales_consultant")["upgrade_amount"]
                    .agg(total="sum", avg="mean")
                    .sort_values("avg", ascending=False)
                    .reset_index()
                )
                ctx_parts.append(f"""
UPGRADE REVENUE ANALYSIS:
- Total upgrade revenue: ${closed["upgrade_amount"].sum():,.0f}
- Avg upgrade per home: ${closed["upgrade_amount"].mean():,.0f}
- Upgrade attach rate: {(closed["upgrade_amount"]>0).mean()*100:.1f}% of closed contracts have upgrades
- Upgrades as % of total revenue: {closed["upgrade_amount"].sum()/closed["contract_price"].sum()*100:.1f}%

By floor plan (sorted by total upgrade revenue):
{upgrade_by_plan.to_string(index=False)}

By region:
{upgrade_by_region.to_string(index=False)}

By consultant (sorted by avg upgrade):
{upgrade_by_consultant.to_string(index=False)}
""")

            # ── 4. Velocity / Days to Close ────────────────────────
            if not closed.empty:
                vel_by_region = (
                    closed.groupby("region")["days_to_close"]
                    .agg(avg="mean", min="min", max="max")
                    .round(1)
                    .reset_index()
                )
                vel_by_consultant = (
                    closed.groupby("sales_consultant")["days_to_close"]
                    .mean().round(1)
                    .sort_values()
                    .reset_index()
                )
                ctx_parts.append(f"""
CLOSE VELOCITY:
- Overall avg days to close: {closed["days_to_close"].mean():.0f} days
- Fastest close: {closed["days_to_close"].min():.0f} days
- Slowest close: {closed["days_to_close"].max():.0f} days

By region:
{vel_by_region.to_string(index=False)}

By consultant (fastest to slowest):
{vel_by_consultant.to_string(index=False)}
""")

            # ── 5. Lead Source Breakdown ───────────────────────────
            source_summary = (
                df_sales.groupby("buyer_source")
                .agg(
                    total=("contract_id","count"),
                    closed=("is_closed","sum"),
                    cancelled=("is_cancelled","sum")
                )
                .reset_index()
            )
            source_summary["close_rate"] = (source_summary["closed"] / source_summary["total"] * 100).round(1)
            source_summary = source_summary.sort_values("closed", ascending=False)
            ctx_parts.append(f"""
LEAD SOURCE PERFORMANCE:
{source_summary.to_string(index=False)}
""")

            # ── 6. Financing Mix ───────────────────────────────────
            if not closed.empty:
                loan_mix = (
                    closed.groupby("loan_type")
                    .agg(count=("contract_id","count"), avg_price=("contract_price","mean"))
                    .reset_index()
                )
                loan_mix["pct"] = (loan_mix["count"] / loan_mix["count"].sum() * 100).round(1)
                loan_mix = loan_mix.sort_values("count", ascending=False)
                ctx_parts.append(f"""
FINANCING MIX (closed contracts):
{loan_mix.to_string(index=False)}
""")

        # ── 7. Community Scorecard ─────────────────────────────────
        if not df_community.empty:
            comm_cols = [
                "community","region","regional_manager",
                "closed_units","sales_target_units","target_attainment_pct",
                "cancellation_rate","avg_contract_price","avg_price_per_sqft",
                "avg_days_to_close","avg_gross_margin_pct","performance_tier",
                "total_upgrade_revenue","avg_upgrade_amount","upgrade_attach_rate",
                "upgrade_pct_of_revenue","revenue_target_est"
            ]
            available_cols = [c for c in comm_cols if c in df_community.columns]
            ctx_parts.append("\nCOMMUNITY SCORECARD (all metrics per community):\n" +
                df_community[available_cols].to_string(index=False))

        # ── 8. Consultant Leaderboard ──────────────────────────────
        if not df_consultant.empty:
            cons_cols = [
                "sales_consultant","region","closed_units","cancelled_units",
                "total_closed_revenue","avg_sale_price","avg_price_per_sqft",
                "avg_days_to_close","cancellation_rate","avg_upgrade_attach_rate",
                "total_upgrade_revenue","referral_close_rate","total_commissions"
            ]
            available_cons = [c for c in cons_cols if c in df_consultant.columns]
            ctx_parts.append("\nCONSULTANT LEADERBOARD (full metrics):\n" +
                df_consultant[available_cons].sort_values("closed_units", ascending=False)
                .to_string(index=False))

        return "\n".join(ctx_parts)

    # ── Chat Interface ──────────────────────────────────────────
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Render prior messages
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Suggested questions
    # Suggested questions
    if not st.session_state.chat_history:
        st.markdown("**Try asking:**")
        suggestions = [
            "Which region has the highest cancellation rate and why might that be?",
            "Who is the top performing sales consultant by closed units and by upgrade revenue?",
            "Which floor plan generates the most upgrade revenue on average?",
            "Which communities are at risk of missing their annual unit targets?",
            "What is the total upgrade revenue and which region contributes the most?",
            "Which lead source has the highest close rate?",
            "What's the financing mix for closed contracts and which loan type is most common?",
        ]
        for s in suggestions:
            if st.button(s, key=s):
                st.session_state.pending_question = s
                st.rerun()

    # Pull pending question from button click into the same flow as typed input
    if "pending_question" in st.session_state and st.session_state.pending_question:
        user_input = st.session_state.pending_question
        st.session_state.pending_question = None
    else:
        user_input = st.chat_input("Ask a question about the sales data...")

    # User input
    user_input = st.chat_input("Ask a question about the sales data...")

    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing data..."):
                try:
                    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
                    data_context = build_data_context(df_sales, df_community, df_consultant)

                    # ── Grounding system prompt ─────────────────────
                    # Anchors Claude strictly to the provided data context.
                    # Prevents hallucination and keeps responses data-driven.
                    system_prompt = """You are a data analyst assistant for Homebuilder Enterprises, a Texas homebuilder.

GROUNDING RULES — follow these strictly:
1. You ONLY answer questions using the data context provided to you in this conversation.
2. If a question cannot be answered from the provided data, respond with exactly:
   "I don't have that information in the current dataset."
3. Never invent, estimate, or extrapolate numbers not present in the data.
4. Always cite specific numbers when answering. Format currency with $ and commas.
5. When performing a calculation, show your work (e.g. "201 closed / 120 target = 167.5% attainment").
6. Reference which data section your answer comes from, e.g.:
   "According to the community scorecard..." or "Based on the consultant leaderboard..."
7. Do not answer questions unrelated to Homebuilder Enterprises sales performance.
8. If you are uncertain whether a number is exact or approximate, say so explicitly."""

                    # ── Grounded message structure ──────────────────
                    # Pattern: data context injected as first user/assistant exchange,
                    # then conversation history, then current question.
                    # This is the standard RAG grounding pattern.
                    messages = [
                        {
                            "role": "user",
                            "content": (
                                "I am providing you with the Homebuilder Enterprises sales dataset. "
                                "This is the ONLY data you are authorized to use when answering questions. "
                                "Do not use any knowledge outside of this data.\n\n"
                                f"=== GROUNDED DATA CONTEXT ===\n{data_context}\n=== END OF DATA CONTEXT ==="
                            )
                        },
                        {
                            "role": "assistant",
                            "content": (
                                "Understood. I have reviewed the Homebuilder Enterprises sales dataset and I am "
                                "grounded exclusively in this data. I will only answer questions based on the "
                                "information provided, cite specific numbers, show my calculations, and reference "
                                "the relevant data section in each response. I will not use any outside knowledge "
                                "or fabricate information not present in the dataset."
                            )
                        }
                    ]

                    # Append prior conversation turns (excluding current question)
                    for m in st.session_state.chat_history[:-1]:
                        messages.append({"role": m["role"], "content": m["content"]})

                    # Append current user question
                    messages.append({"role": "user", "content": user_input})

                    response = client.messages.create(
                        model="claude-sonnet-4-6",
                        max_tokens=4000,
                        system=system_prompt,
                        messages=messages,
                    )
                    answer = response.content[0].text
                    st.markdown(answer)
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})

                except Exception as e:
                    err_msg = f"⚠️ Error calling AI: {str(e)}"
                    st.error(err_msg)
                    st.session_state.chat_history.append({"role": "assistant", "content": err_msg})

    if st.session_state.chat_history:
        if st.button("🗑️ Clear conversation"):
            st.session_state.chat_history = []
            st.rerun()
