"""
dashboard/charts.py
===================
Input dataFrames, output Plotly figures.
No st.* calls anywhere in this file — keeps charts testable
and reusable in app.py without modification.

All functions expect pre-aggregated DataFrames from dashboard/data.py.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Consistent colour palette across all charts
_PALETTE = px.colors.qualitative.Safe


def build_category_bar(cat_df: pd.DataFrame) -> go.Figure:
    """
    Horizontal bar chart — total spend per category.

    Expects agg_by_category() output:
        columns: category (str), spent (float, positive)
        sorted:  descending by spent
    """
    if cat_df.empty:
        return _empty_figure("No expense data for selected filters.")

    fig = px.bar(
        cat_df.sort_values("spent", ascending=True),  # ascending so largest is at top
        x="spent",
        y="category",
        orientation="h",
        text=cat_df.sort_values("spent", ascending=True)["spent"].apply(
            lambda v: f"SGD {v:,.0f}"
        ),
        labels={"spent": "SGD", "category": ""},
        color="category",
        color_discrete_sequence=_PALETTE,
    )
    fig.update_traces(textposition="outside", showlegend=False)
    fig.update_layout(
        title="Spend by Category",
        margin=dict(l=0, r=80, t=40, b=0),
        height=380,
        showlegend=False,
        xaxis_title="",
    )
    return fig


def build_category_share_bar(share_df: pd.DataFrame) -> go.Figure:
    """
    Horizontal bar showing each category's % share of total spend.
    Replaces pie/donut chart — same information, easier to compare.

    Expects agg_category_share() output:
        columns: category, spent, share_pct
    """
    if share_df.empty:
        return _empty_figure("No expense data for selected filters.")

    df = share_df.sort_values("share_pct", ascending=True)

    fig = px.bar(
        df,
        x="share_pct",
        y="category",
        orientation="h",
        text=df["share_pct"].apply(lambda v: f"{v:.1f}%"),
        labels={"share_pct": "% of Total Spend", "category": ""},
        color="category",
        color_discrete_sequence=_PALETTE,
    )
    fig.update_traces(textposition="outside", showlegend=False)
    fig.update_layout(
        title="Category Share of Total Spend",
        margin=dict(l=0, r=60, t=40, b=0),
        height=380,
        showlegend=False,
        xaxis=dict(ticksuffix="%", range=[0, max(df["share_pct"]) * 1.25]),
        xaxis_title="",
    )
    return fig


def build_monthly_trend_bar(trend_df: pd.DataFrame) -> go.Figure:
    """
    Stacked vertical bar — spend per category per month.

    Expects agg_monthly_trend() output:
        columns: month (str 'YYYY-MM'), category, spent (float, positive)
    """
    if trend_df.empty:
        return _empty_figure("No trend data for selected filters.")

    fig = px.bar(
        trend_df,
        x="month",
        y="spent",
        color="category",
        barmode="stack",
        labels={"spent": "SGD", "month": "Month", "category": "Category"},
        color_discrete_sequence=_PALETTE,
    )
    fig.update_layout(
        title="Monthly Spending Trend",
        margin=dict(l=0, r=0, t=40, b=0),
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=-0.45),
        xaxis_title="",
    )
    return fig


def build_daily_spend_bar(daily_df: pd.DataFrame) -> go.Figure:
    """
    Stacked vertical bar — spend by day of month.

    Expects agg_daily_spend() output:
        columns: day (int), category, spent (float, positive)
    """
    if daily_df.empty:
        return _empty_figure("No daily data for selected filters.")

    fig = px.bar(
        daily_df,
        x="day",
        y="spent",
        color="category",
        barmode="stack",
        labels={"spent": "SGD", "day": "Day of Month", "category": "Category"},
        color_discrete_sequence=_PALETTE,
    )
    fig.update_layout(
        title="Daily Spending",
        margin=dict(l=0, r=0, t=40, b=0),
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=-0.45),
        xaxis=dict(dtick=1),
        xaxis_title="",
    )
    return fig


def build_top_merchants_bar(merch_df: pd.DataFrame) -> go.Figure:
    """
    Horizontal bar — top merchants by total spend, coloured by category.

    Expects agg_top_merchants() output:
        columns: merchant, category, total (float, positive), txns (int)
    """
    if merch_df.empty:
        return _empty_figure("No merchant data for selected filters.")

    df = merch_df.sort_values("total", ascending=True)

    fig = px.bar(
        df,
        x="total",
        y="merchant",
        orientation="h",
        color="category",
        text=df["total"].apply(lambda v: f"SGD {v:,.0f}"),
        labels={"total": "SGD", "merchant": "", "category": "Category"},
        hover_data={"txns": True},
        color_discrete_sequence=_PALETTE,
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        title="Top Merchants by Spend",
        margin=dict(l=0, r=80, t=40, b=0),
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=-0.45),
        xaxis_title="",
    )
    return fig


def build_income_vs_spend_bar(df_month_scope: pd.DataFrame) -> go.Figure:
    """
    Grouped bar — Income vs Spend per month side-by-side.
    Uses the month-scoped (unfiltered by category) DataFrame.
    """
    if df_month_scope.empty:
        return _empty_figure("No data.")

    income = (
        df_month_scope[df_month_scope["amount"] > 0]
        .groupby("month")["amount"].sum()
        .reset_index()
        .rename(columns={"amount": "value"})
        .assign(type="Income")
    )
    spend = (
        df_month_scope[df_month_scope["amount"] < 0]
        .groupby("month")["amount"].sum().abs()
        .reset_index()
        .rename(columns={"amount": "value"})
        .assign(type="Spend")
    )
    combined = pd.concat([income, spend], ignore_index=True)

    fig = px.bar(
        combined,
        x="month",
        y="value",
        color="type",
        barmode="group",
        labels={"value": "SGD", "month": "Month", "type": ""},
        color_discrete_map={"Income": "#2ecc71", "Spend": "#e74c3c"},
    )
    fig.update_layout(
        title="Income vs Spend by Month",
        margin=dict(l=0, r=0, t=40, b=0),
        height=340,
        legend=dict(orientation="h", yanchor="bottom", y=-0.35),
        xaxis_title="",
    )
    return fig


# ── Internal helpers ──────────────────────────────────────────────────────────

def _empty_figure(message: str) -> go.Figure:
    """Returns a blank figure with a centred message — avoids silent empty plots."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=14, color="grey"),
    )
    fig.update_layout(
        height=300,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=0, r=0, t=0, b=0),
    )
    return fig